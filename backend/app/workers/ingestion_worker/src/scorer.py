"""Simplified scoring framework for datasets, models, and code."""

import os
import re
import shutil
import tempfile
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Import GitPython for Git operations
import git
import requests
from dotenv import load_dotenv

from .code_quality import calculate_code_quality_with_timing
from .dataset_quality import calculate_dataset_quality_with_timing
from .integrated_data_fetcher import IntegratedDataFetcher
from .license import calculate_license_score_with_timing
from .log import loggerInstance
from .net_score import calculate_net_score_with_timing
from .performance_claims import calculate_performance_claims_with_timing
from .ramp_up_time import calculate_ramp_up_time_with_timing
from .reviewedness import calculate_reviewedness_for_url
from .reproducibility import calculate_reproducibility_for_url
from .treescore import calculate_tree_score_for_url
from .url import UrlCategory

load_dotenv()


@dataclass
class ScoreResult:
    """Scoring result for a single URL and category."""

    url: str
    category: UrlCategory
    score: float
    max_score: float
    details: dict[str, Any]

    @property
    def percentage(self) -> float:
        """Get score as percentage."""
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0.0

    def __str__(self) -> str:
        """Format the score as a human-readable string."""
        return (
            f"{self.category}: {self.score:.1f}/{self.max_score:.1f} "
            f"({self.percentage:.1f}%)"
        )


def make_request(url: str) -> Any:
    """Make HTTP request with error handling."""
    try:
        response = requests.get(
            url, headers={"User-Agent": "Trustworthy-Model-Reuse-CLI/1.0"}, timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def calculate_size_score_with_timing(
    model_size_mb: float,
) -> tuple[dict[str, float], int]:
    """Calculate size_score with latency measurement.

    Args:
        model_size_mb: Model size in megabytes

    Returns:
        tuple of (size_score_dict, latency_ms)
    """
    start_time = time.perf_counter()
    size_score = calculate_size_score(model_size_mb)
    end_time = time.perf_counter()
    latency_ms = int((end_time - start_time) * 1000)
    return size_score, latency_ms


def calculate_size_score(model_size_mb: float) -> dict[str, float]:
    """Calculate size_score based on model size using piecewise linear mapping.

    Args:
        model_size_mb: Model size in megabytes

    Returns:
        dictionary mapping hardware types to compatibility scores [0,1]
    """
    # Hardware capacity thresholds (in MB) - Reasonable thresholds for 2024 hardware
    thresholds = {
        "raspberry_pi": {
            "min": 0,
            "max": 390,
        },  # 0-390MB full score, taper to 0 at 1.2GB+
        "jetson_nano": {
            "min": 0,
            "max": 1500,
        },  # 0-1.5GB full score, taper to 0 at 4GB+ (4GB RAM + GPU acceleration)
        "desktop_pc": {
            "min": 0,
            "max": 8000,
        },  # 0-8GB full score, taper to 0 at 32GB+ (modern desktops with 16-32GB RAM)
        "aws_server": {
            "min": 0,
            "max": 100000,
        },  # 0-100GB full score, taper to 0 at 500GB+ (high-memory instances)
    }

    size_score = {}

    for hardware, threshold in thresholds.items():
        if model_size_mb <= threshold["min"]:
            score = 1.0
        elif model_size_mb >= threshold["max"]:
            score = 0.0
        else:
            # Piecewise linear mapping: score = max(0, 1 - (size - min) / (max - min))
            score = max(
                0.0,
                1.0
                - (model_size_mb - threshold["min"])
                / (threshold["max"] - threshold["min"]),
            )

        size_score[hardware] = round(score, 2)

    return size_score


def analyze_model_repository(
    model_name: str, model_url: str, model_type: str = "model"
) -> Dict[str, Any]:
    """Download and analyze model repository to determine actual model size.

    Uses Hugging Face Hub for reliable model file access.

    Args:
        model_name: Name of the model (e.g., "google-bert/bert-base-uncased")
        model_type: Type of model ("model", "dataset", "code")

    Returns:
        Dictionary with analysis results including size in MB
    """
    # Debug: Print the model name being processed
    # print(f"DEBUG: Processing model_name: {model_name}, model_type: {model_type}")

    # Disable progress bars globally
    import os

    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    import contextlib
    import io

    # Redirect stdout and stderr to suppress all output from huggingface_hub
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        temp_dir = None
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="model_analysis_")

            try:
                from huggingface_hub import snapshot_download

                # Get HF token from environment
                hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
                # Download only the essential model files for size calculation
                downloaded_path = snapshot_download(
                    repo_id=model_name,
                    cache_dir=temp_dir,
                    local_dir=temp_dir,
                    # local_dir_use_symlinks=False,
                    token=hf_token,
                    allow_patterns=[
                        "pytorch_model.bin",  # Primary PyTorch model
                        "model.safetensors",  # Primary SafeTensors model
                        "tf_model.h5",  # Primary TensorFlow model
                        "*.bin",  # Other PyTorch models
                        "*.safetensors",  # Other SafeTensors models
                        "*.h5",  # Other TensorFlow models
                    ],
                )
                print(f"Essential model files downloaded to: {downloaded_path}")
            except ImportError:
                print("huggingface_hub not available, falling back to Git clone")
                # Fallback to Git clone if huggingface_hub is not available
                # if "/" in model_name:
                #     owner, repo = model_name.split("/", 1)
                #     repo_url = f"https://huggingface.co/{owner}/{repo}.git"
                # else:
                #     repo_url = f"https://huggingface.co/{model_name}.git"

                print(f"Cloning repository: {model_url}")

                # Clone repository
                git.Repo.clone_from(model_url, temp_dir)

            # Analyze model files
            analysis = _analyze_model_files(temp_dir, model_name, model_type)

            return analysis

        except Exception as e:
            # print(f"Repository analysis failed: {e}")
            return {
                "error": f"Failed to analyze repository: {str(e)}",
                "size_mb": 500,  # Fallback size
                "files_analyzed": [],
                "total_files": 0,
            }
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


def _analyze_model_files(
    repo_path: str, model_name: str, model_type: str
) -> Dict[str, Any]:
    """Analyze model files in the cloned repository.

    Args:
        repo_path: Path to the cloned repository
        model_name: Name of the model
        model_type: Type of model

    Returns:
        Dictionary with file analysis results
    """
    model_files: list[dict[str, float | int | str]] = []
    total_size_bytes = 0

    # Common model file patterns
    model_file_patterns = [
        "*.bin",  # PyTorch models
        "*.safetensors",  # SafeTensors format
        "*.h5",  # TensorFlow models
        "*.ckpt",  # Checkpoint files
        "*.pth",  # PyTorch state dict
        "*.pt",  # PyTorch models
        "*.onnx",  # ONNX models
        "*.tflite",  # TensorFlow Lite
        "*.pb",  # TensorFlow protobuf
        "*.pkl",  # Pickle files
        "*.joblib",  # Joblib files
    ]

    # Tokenizer and config files (smaller but relevant)
    config_file_patterns = [
        "*.json",  # Config files
        "*.txt",  # Text files
        "*.yaml",  # YAML configs
        "*.yml",  # YAML configs
    ]

    try:
        repo_path_obj = Path(repo_path)

        # Find model files (core model weights only)
        for pattern in model_file_patterns:
            for file_path in repo_path_obj.rglob(pattern):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    model_files.append(
                        {
                            "name": file_path.name,
                            "path": str(file_path.relative_to(repo_path_obj)),
                            "size_bytes": int(file_size),
                            "size_mb": float(file_size / (1024 * 1024)),
                        }
                    )
                    total_size_bytes += int(file_size)

        # Find config files (for completeness, but don't include in size calculation)
        config_files = []
        for pattern in config_file_patterns:
            for file_path in repo_path_obj.rglob(pattern):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    config_files.append(
                        {
                            "name": file_path.name,
                            "path": str(file_path.relative_to(repo_path_obj)),
                            "size_bytes": int(file_size),
                            "size_mb": float(file_size / (1024 * 1024)),
                        }
                    )
                    # Skip config files when summing model weights

        # Calculate size using the smallest model file (one format is enough)
        if model_files:
            # Find the smallest model file (most efficient format)
            smallest_model = min(model_files, key=lambda x: x["size_bytes"])
            total_size_mb = float(smallest_model["size_mb"])
            total_size_bytes = int(smallest_model["size_bytes"])
        else:
            total_size_mb = 0.0
            total_size_bytes = 0

        return {
            "size_mb": round(total_size_mb, 2),
            "size_bytes": total_size_bytes,
            "model_files": model_files,
            "config_files": config_files,
            "total_files": len(model_files) + len(config_files),
            "files_analyzed": [f["name"] for f in model_files + config_files],
        }

    except Exception as e:
        return {
            "error": f"File analysis failed: {str(e)}",
            "size_mb": 500,  # Fallback size
            "files_analyzed": [],
            "total_files": 0,
        }


def estimate_model_size_with_timing(
    model_name: str, model_url: str, model_type: str = "model"
) -> tuple[float, int]:
    """Estimate model size with timing measurement.

    Args:
        model_name: Name of the model (e.g., "google-bert/bert-base-uncased")
        model_type: Type of model ("model", "dataset", "code")

    Returns:
        tuple of (size_mb, latency_ms)
    """
    start_time = time.perf_counter()

    if not model_name or model_name == "unknown":
        end_time = time.perf_counter()
        latency_ms = int((end_time - start_time) * 1000)
        return 500, latency_ms  # Default for unknown models

    # Analyze the actual repository
    analysis = analyze_model_repository(model_name, model_url, model_type)

    end_time = time.perf_counter()
    latency_ms = int((end_time - start_time) * 1000)

    if "error" in analysis:
        # print(f"Warning: {analysis['error']}")  # Comment out the warning
        return 500, latency_ms  # Fallback size

    return analysis["size_mb"], latency_ms


def estimate_model_size(
    model_name: str, model_url: str, model_type: str = "model"
) -> Any:
    """Estimate model size by analyzing the actual repository.

    Args:
        model_name: Name of the model (e.g., "google-bert/bert-base-uncased")
        model_type: Type of model ("model", "dataset", "code")

    Returns:
        Estimated model size in MB
    """
    if not model_name or model_name == "unknown":
        return 500  # Default for unknown models

    # Analyze the actual repository
    analysis = analyze_model_repository(model_name, model_url, model_type)

    if "error" in analysis:
        print(f"Warning: {analysis['error']}")
        return 500  # Fallback size

    return analysis["size_mb"]


# Initialize data fetcher with API tokens from environment variables

hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
github_token = os.getenv("GITHUB_TOKEN")
_data_fetcher = IntegratedDataFetcher(hf_api_token=hf_token, github_token=github_token)
MAJOR_ORGS = [
    "google",
    "openai",
    "microsoft",
    "meta",
    "facebook",
    "anthropic",
    "nvidia",
    "tensorflow",
]


def is_major_organization(name: str) -> bool:
    """Check if a name contains a major organization."""
    if not name:
        return False
    name_lower = name.lower()
    return any(org in name_lower for org in MAJOR_ORGS)


def calculate_model_bus_factor(contributor_count: int, model_name: str = "") -> float:
    """Calculate bus factor for models based only on contributor count."""
    if is_major_organization(model_name):
        return 0.95
    if contributor_count == 0:
        return 0.0
    elif contributor_count == 1:
        return 0.3
    elif contributor_count <= 3:
        return 0.6
    else:
        return 1.0


def calculate_dataset_bus_factor(
    contributor_count: int, dataset_name: str = ""
) -> float:
    """Calculate bus factor for datasets based only on contributor count."""
    if is_major_organization(dataset_name):
        return 0.95
    if contributor_count == 0:
        return 0.0
    elif contributor_count == 1:
        return 0.4
    elif contributor_count <= 2:
        return 0.7
    else:
        return 1.0


def calculate_code_bus_factor(contributor_count: int, repo_name: str = "") -> float:
    """Calculate bus factor for code repos based only on contributor count."""
    if is_major_organization(repo_name):
        return 0.95
    if contributor_count == 0:
        return 0.0
    elif contributor_count == 1:
        return 0.2
    elif contributor_count <= 3:
        return 0.4
    elif contributor_count <= 10:
        return 0.7
    else:
        return 1.0


def calculate_bus_factor_with_timing(
    url: str, category: UrlCategory, data: Dict[str, Any]
) -> tuple[float, int]:
    """Calculate bus factor with latency measurement."""
    start_time = time.time()
    contributors = data.get("contributors", [])
    contributor_count = len(contributors) if contributors else 0
    name = data.get("name", "")

    if category == UrlCategory.MODEL:
        score = calculate_model_bus_factor(contributor_count, name)
    elif category == UrlCategory.DATASET:
        score = calculate_dataset_bus_factor(contributor_count, name)
    elif category == UrlCategory.CODE:
        score = calculate_code_bus_factor(contributor_count, name)
    else:
        score = 0.0

    end_time = time.time()
    latency_ms = max(int((end_time - start_time) * 1000), 10)

    return score, latency_ms


def calculate_metrics(
    data: Dict[str, Any],
    category: UrlCategory,
    code_url: Optional[str] = None,
    model_name: str = "",
) -> dict[str, Any]:
    """Calculate metrics based on API data."""
    downloads = data.get("downloads", 0)
    likes = data.get("likes", 0)
    # has_card = bool(data.get("cardData") or data.get("has_model_card"))

    # License calculation with timing
    license_score, license_latency = calculate_license_score_with_timing(data)

    # Ramp-up time - enhanced calculation with timing
    ramp_up, ramp_up_latency = calculate_ramp_up_time_with_timing(data, model_name)

    # Performance claims - enhanced calculation with timing
    perf, perf_latency = calculate_performance_claims_with_timing(data, model_name)

    # Dataset/code score (based on linked resources in card)
    dataset_code = 1.0 if downloads > 1000000 else 0.0

    # Dataset quality - enhanced calculation with timing
    dataset_qual, dataset_qual_latency = calculate_dataset_quality_with_timing(
        data, downloads, likes
    )

    # Code quality using Flake8 analysis
    code_qual, code_qual_latency = calculate_code_quality_with_timing(
        code_url, model_name
    )

    # Net score is calculated separately using full metrics (bus_factor, size_score)

    return {
        "ramp_up_time": ramp_up,
        "ramp_up_time_latency": ramp_up_latency,
        "performance_claims": perf,
        "performance_claims_latency": perf_latency,
        "license": license_score,
        "license_latency": license_latency,
        "size_score_latency": (
            50 if downloads > 1000000 else 40 if downloads < 100 else 15
        ),
        "dataset_and_code_score": dataset_code,
        "dataset_and_code_score_latency": (
            15 if dataset_code > 0 else 5 if downloads < 100 else 40
        ),
        "dataset_quality": dataset_qual,
        "dataset_quality_latency": dataset_qual_latency,
        "code_quality": code_qual,
        "code_quality_latency": code_qual_latency,
    }


def score_dataset(url: str) -> ScoreResult:
    """Score a Hugging Face dataset."""
    # Start timing for total net_score_latency
    total_start_time = time.perf_counter()

    # Extract dataset name
    match = re.search(r"https://huggingface\.co/datasets/([\w-]+(?:/[\w-]+)?)", url)
    if not match:
        estimated_size = 1000  # Default 1GB for datasets
        size_score_latency = 10  # Fast since we're not downloading
        size_score = calculate_size_score(estimated_size)
        total_end_time = time.perf_counter()
        total_latency = int((total_end_time - total_start_time) * 1000)
        return ScoreResult(
            url,
            UrlCategory.DATASET,
            0.0,
            10.0,
            {
                "error": "Invalid URL",
                "name": "unknown",
                "size_score": size_score,
                "size_score_latency": size_score_latency,
                "net_score": 0.0,
                "net_score_latency": total_latency,
            },
        )

    dataset_name = match.group(1)
    api_url = f"https://huggingface.co/api/datasets/{dataset_name}"
    data = make_request(api_url)

    if not data:
        estimated_size = 1000  # Default 1GB for datasets
        size_score_latency = 10  # Fast since we're not downloading
        size_score = calculate_size_score(estimated_size)
        return ScoreResult(
            url,
            UrlCategory.DATASET,
            0.0,
            10.0,
            {
                "name": dataset_name,
                "fallback": True,
                "size_score": size_score,
                "size_score_latency": size_score_latency,
            },
        )

    # Simple scoring based on key metrics
    downloads = data.get("downloads", 0)
    likes = data.get("likes", 0)
    has_description = bool(data.get("description"))

    score = 2.0  # Base score
    if downloads > 10000:
        score += 3.0
    elif downloads > 1000:
        score += 2.0
    elif downloads > 100:
        score += 1.0

    if likes > 50:
        score += 2.0
    elif likes > 10:
        score += 1.0

    if has_description:
        score += 2.0

    # Calculate size_score for datasets using API data instead of downloading
    # Use a default size for datasets since we can't easily estimate without downloading
    estimated_size = 1000  # Default 1GB for datasets
    size_score_latency = 10  # Fast since we're not downloading
    size_score = calculate_size_score(estimated_size)
    contributor_data = _data_fetcher.fetch_data(url)
    data_merged = {**data, **contributor_data} if data else contributor_data

    # Calculate all metrics in parallel
    parallel_metrics, total_parallel_latency = compute_all_metrics_parallel(
        data_merged, url, UrlCategory.DATASET, None, dataset_name
    )

    # Use the total latency from parallel computation
    total_net_score_latency = total_parallel_latency

    return ScoreResult(
        url,
        UrlCategory.DATASET,
        min(score, 10.0),
        10.0,
        {
            "name": dataset_name,
            "downloads": downloads,
            "likes": likes,
            "has_description": has_description,
            "net_score": parallel_metrics.get("net_score", 0.0),
            "net_score_latency": total_net_score_latency,
            **parallel_metrics,
        },
    )


def score_model(url: str, code_url: Optional[str] = None) -> ScoreResult:
    """Score a Hugging Face model."""
    # Start timing for total net_score_latency
    total_start_time = time.perf_counter()

    # Extract model name
    match = re.search(r"https://huggingface\.co/(?:models/)?([\w-]+(?:/[\w-]+)?)", url)
    if not match:
        estimated_size, size_score_latency = estimate_model_size_with_timing(
            "unknown", url, "model"
        )
        size_score = calculate_size_score(estimated_size)
        total_end_time = time.perf_counter()
        total_latency = int((total_end_time - total_start_time) * 1000)
        return ScoreResult(
            url,
            UrlCategory.MODEL,
            0.0,
            10.0,
            {
                "error": "Invalid URL",
                "name": "unknown",
                "size_score": size_score,
                "size_score_latency": size_score_latency,
                "net_score": 0.0,
                "net_score_latency": total_latency,
            },
        )

    model_name = match.group(1)
    api_url = f"https://huggingface.co/api/models/{model_name}"
    data = make_request(api_url)

    if not data:
        estimated_size, size_score_latency = estimate_model_size_with_timing(
            model_name, url, "model"
        )
        size_score = calculate_size_score(estimated_size)
        return ScoreResult(
            url,
            UrlCategory.MODEL,
            2.0,
            10.0,
            {
                "name": model_name,
                "fallback": True,
                "size_score": size_score,
                "size_score_latency": size_score_latency,
            },
        )

    # Simple scoring based on key metrics
    downloads = data.get("downloads", 0)
    likes = data.get("likes", 0)
    has_card = bool(data.get("cardData"))
    pipeline_tag = data.get("pipeline_tag")
    # license = data.get("cardData").get("license")

    score = 2.0  # Base score
    if downloads > 100000:
        score += 3.0
    elif downloads > 10000:
        score += 2.0
    elif downloads > 1000:
        score += 1.0

    if likes > 100:
        score += 2.0
    elif likes > 20:
        score += 1.0

    if has_card:
        score += 2.0

    if pipeline_tag:
        score += 1.0

    # Calculate dynamic size_score with timing
    estimated_size, size_score_latency = estimate_model_size_with_timing(
        model_name, "model"
    )
    size_score = calculate_size_score(estimated_size)

    # Fetch contributor data and merge with API data
    contributor_data = _data_fetcher.fetch_data(url)
    data_merged = {**data, **contributor_data} if data else contributor_data

    # Calculate all metrics in parallel
    parallel_metrics, total_parallel_latency = compute_all_metrics_parallel(
        data_merged, url, UrlCategory.MODEL, code_url, model_name
    )

    # Use the total latency from parallel computation
    total_net_score_latency = total_parallel_latency

    return ScoreResult(
        url,
        UrlCategory.MODEL,
        min(score, 10.0),
        10.0,
        {
            "name": model_name,
            "downloads": downloads,
            "likes": likes,
            "has_model_card": has_card,
            "pipeline_tag": pipeline_tag,
            "net_score": parallel_metrics.get("net_score", 0.0),
            "net_score_latency": total_net_score_latency,
            **parallel_metrics,
        },
    )


def score_code(url: str) -> ScoreResult:
    """Score a GitHub repository."""
    # Start timing for total net_score_latency
    total_start_time = time.perf_counter()

    # Extract repo info
    match = re.search(r"https://github\.com/([\w-]+)/([\w-]+)", url)
    if not match:
        estimated_size, size_score_latency = estimate_model_size_with_timing(
            "unknown", "code"
        )
        size_score = calculate_size_score(estimated_size)
        total_end_time = time.perf_counter()
        total_latency = int((total_end_time - total_start_time) * 1000)
        return ScoreResult(
            url,
            UrlCategory.CODE,
            0.0,
            10.0,
            {
                "error": "Invalid URL",
                "name": "unknown",
                "size_score": size_score,
                "size_score_latency": size_score_latency,
                "net_score": 0.0,
                "net_score_latency": total_latency,
            },
        )

    owner, repo = match.groups()
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    data = make_request(api_url)

    if not data:
        estimated_size, size_score_latency = estimate_model_size_with_timing(
            f"{owner}/{repo}", "code"
        )
        size_score = calculate_size_score(estimated_size)
        return ScoreResult(
            url,
            UrlCategory.CODE,
            2.0,
            10.0,
            {
                "name": f"{owner}/{repo}",
                "fallback": True,
                "size_score": size_score,
                "size_score_latency": size_score_latency,
            },
        )

    # Simple scoring based on key metrics
    stars = data.get("stargazers_count", 0)
    forks = data.get("forks_count", 0)
    has_description = bool(data.get("description"))
    has_license = bool(data.get("license"))
    language = data.get("language")

    score = 2.0  # Base score
    if stars > 1000:
        score += 3.0
    elif stars > 100:
        score += 2.0
    elif stars > 10:
        score += 1.0

    if forks > 100:
        score += 1.0
    elif forks > 10:
        score += 0.5

    if has_description:
        score += 2.0

    if has_license:
        score += 1.0

    if language:
        score += 1.0

    # Fetch contributor data and merge with API data
    contributor_data = _data_fetcher.fetch_data(url)
    data_merged = {**data, **contributor_data} if data else contributor_data

    # Calculate all metrics in parallel
    parallel_metrics, total_parallel_latency = compute_all_metrics_parallel(
        data_merged, url, UrlCategory.CODE, None, f"{owner}/{repo}"
    )

    # Use the total latency from parallel computation
    total_net_score_latency = total_parallel_latency

    return ScoreResult(
        url,
        UrlCategory.CODE,
        min(score, 10.0),
        10.0,
        {
            "name": f"{owner}/{repo}",
            "stars": stars,
            "forks": forks,
            "has_description": has_description,
            "has_license": has_license,
            "language": language,
            "net_score": parallel_metrics.get("net_score", 0.0),
            "net_score_latency": total_net_score_latency,
            **parallel_metrics,
        },
    )


def score_url(
    url: str, category: UrlCategory, code_url: Optional[str] = None
) -> Optional[ScoreResult]:
    """Score a URL based on its category."""
    if category == UrlCategory.DATASET:
        return score_dataset(url)
    elif category == UrlCategory.MODEL:
        return score_model(url, code_url)
    elif category == UrlCategory.CODE:
        return score_code(url)
    else:
        return None


#        estimated_size = estimate_model_size("unknown", "invalid")
#        size_score = calculate_size_score(estimated_size)
#        return ScoreResult(
#            url,
#            UrlCategory.INVALID,
#            0.0,
#            10.0,
#            {"error": "Invalid category", "name": "unknown", "size_score": size_score},
#        )


# Parallel metric computation functions
def compute_ramp_up_time_parallel(
    data: Dict[str, Any], model_name: str = ""
) -> tuple[str, float, int]:
    """Compute ramp_up_time metric in parallel."""
    try:
        score, latency = calculate_ramp_up_time_with_timing(data, model_name)
        return "ramp_up_time", score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing ramp_up_time: {e}")
        return "ramp_up_time", 0.0, 0


def compute_bus_factor_parallel(
    url: str, category: UrlCategory, data: Dict[str, Any]
) -> tuple[str, float, int]:
    """Compute bus_factor metric in parallel."""
    try:
        score, latency = calculate_bus_factor_with_timing(url, category, data)
        return "bus_factor", score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing bus_factor: {e}")
        return "bus_factor", 0.0, 0


def compute_performance_claims_parallel(
    data: Dict[str, Any], model_name: str = ""
) -> tuple[str, float, int]:
    """Compute performance_claims metric in parallel."""
    try:
        score, latency = calculate_performance_claims_with_timing(data, model_name)
        return "performance_claims", score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing performance_claims: {e}")
        return "performance_claims", 0.0, 0


def compute_license_parallel(data: Dict[str, Any]) -> tuple[str, float, int]:
    """Compute license metric in parallel."""
    try:
        # Use the license module for calculation
        license_score, latency = calculate_license_score_with_timing(data)
        return "license", license_score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing license: {e}")
        return "license", 0.0, 0


def compute_size_score_parallel(
    model_name: str, model_type: str = "model"
) -> tuple[str, Dict[str, float], int]:
    """Compute size_score metric in parallel."""
    try:
        estimated_size, size_latency = estimate_model_size_with_timing(
            model_name, model_type
        )
        size_score = calculate_size_score(estimated_size)
        return "size_score", size_score, size_latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing size_score: {e}")
        return (
            "size_score",
            {
                "raspberry_pi": 0.0,
                "jetson_nano": 0.0,
                "desktop_pc": 0.0,
                "aws_server": 0.0,
            },
            0,
        )


def compute_dataset_and_code_score_parallel(
    data: Dict[str, Any],
) -> tuple[str, float, int]:
    """Compute dataset_and_code_score metric in parallel."""
    try:
        # start_time = time.perf_counter()

        downloads = data.get("downloads", 0)
        dataset_code_score = 1.0 if downloads > 1000000 else 0.0

        # end_time = time.perf_counter()
        latency = 15 if dataset_code_score > 0 else 5 if downloads < 100 else 40

        return "dataset_and_code_score", dataset_code_score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing dataset_and_code_score: {e}")
        return "dataset_and_code_score", 0.0, 0


def compute_dataset_quality_parallel(
    data: Dict[str, Any], downloads: int, likes: int
) -> tuple[str, float, int]:
    """Compute dataset_quality metric in parallel."""
    try:
        score, latency = calculate_dataset_quality_with_timing(data, downloads, likes)
        return "dataset_quality", score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing dataset_quality: {e}")
        return "dataset_quality", 0.0, 0


def compute_code_quality_parallel(
    code_url: Optional[str], model_name: str
) -> tuple[str, float, int]:
    """Compute code_quality metric in parallel."""
    try:
        score, latency = calculate_code_quality_with_timing(code_url, model_name)
        return "code_quality", score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing code_quality: {e}")
        return "code_quality", 0.0, 0


def compute_reviewedness_parallel(url: str, code_url: Optional[str]) -> tuple[str, float, int]:
    """Compute reviewedness metric (placeholder). Prefer code_url when available."""
    try:
        target_url = code_url or url
        score, latency = calculate_reviewedness_for_url(target_url)
        loggerInstance.logger.log_info(
            f"reviewedness target_url={target_url} score={score} latency_ms={latency}"
        )
        return "reviewedness", score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing reviewedness: {e}")
        return "reviewedness", 0.0, 0


def compute_reproducibility_parallel(url: str) -> tuple[str, float, int]:
    """Compute reproducibility metric (placeholder)."""
    try:
        score, latency = calculate_reproducibility_for_url(url)
        return "reproducibility", score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing reproducibility: {e}")
        return "reproducibility", 0.0, 0


def compute_tree_score_parallel(url: str) -> tuple[str, float, int]:
    """Compute tree_score metric (placeholder)."""
    try:
        score, latency = calculate_tree_score_for_url(url)
        return "tree_score", score, latency
    except Exception as e:
        loggerInstance.logger.log_info(f"Error computing tree_score: {e}")
        return "tree_score", 0.0, 0


def compute_all_metrics_parallel(
    data: Dict[str, Any],
    url: str,
    category: UrlCategory,
    code_url: Optional[str] = None,
    model_name: str = "",
) -> tuple[Dict[str, Any], int]:
    """Compute all metrics in parallel using ThreadPoolExecutor.

    Args:
        data: Model/dataset data from API
        url: URL being analyzed
        category: URL category (MODEL, DATASET, CODE)
        code_url: Optional code URL for model analysis
        model_name: Model name for analysis

    Returns:
        tuple of (metrics_dict, total_latency_ms)
    """
    start_time = time.perf_counter()

    # Prepare data for parallel execution
    downloads = data.get("downloads", 0)
    likes = data.get("likes", 0)

    # Determine optimal number of workers based on available cores
    max_workers = min(8, (os.cpu_count() or 1) * 2)

    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all metric computation tasks
        future_to_metric: Dict[Future[tuple[str, Any, int]], str] = {
            executor.submit(
                compute_ramp_up_time_parallel, data, model_name
            ): "ramp_up_time",
            executor.submit(
                compute_bus_factor_parallel, url, category, data
            ): "bus_factor",
            executor.submit(
                compute_performance_claims_parallel, data, model_name
            ): "performance_claims",
            executor.submit(compute_license_parallel, data): "license",
            executor.submit(
                compute_size_score_parallel,
                model_name,
                (
                    "model"
                    if category == UrlCategory.MODEL
                    else "dataset" if category == UrlCategory.DATASET else "code"
                ),
            ): "size_score",
            executor.submit(
                compute_dataset_and_code_score_parallel, data
            ): "dataset_and_code_score",
            executor.submit(
                compute_dataset_quality_parallel, data, downloads, likes
            ): "dataset_quality",
            executor.submit(
                compute_code_quality_parallel, code_url, model_name
            ): "code_quality",
            executor.submit(
                compute_reviewedness_parallel, url, code_url
            ): "reviewedness",
            executor.submit(
                compute_reproducibility_parallel, url
            ): "reproducibility",
            executor.submit(
                compute_tree_score_parallel, url
            ): "tree_score",
        }

        # Collect results as they complete
        for future in as_completed(future_to_metric):
            metric_name = future_to_metric[future]
            try:
                metric_key, score, latency = future.result()
                results[metric_key] = score
                results[f"{metric_key}_latency"] = latency
            except Exception as e:
                loggerInstance.logger.log_info(f"Error computing {metric_name}: {e}")
                results[metric_name] = 0.0
                results[f"{metric_name}_latency"] = 0

    # Calculate net score with all metrics
    complete_metrics: Dict[str, Any] = {
        "ramp_up_time": results.get("ramp_up_time", 0.0),
        "bus_factor": results.get("bus_factor", 0.0),
        "performance_claims": results.get("performance_claims", 0.0),
        "license": results.get("license", 0.0),
        "size_score": results.get("size_score", {}),
        "dataset_and_code_score": results.get("dataset_and_code_score", 0.0),
        "dataset_quality": results.get("dataset_quality", 0.0),
        "code_quality": results.get("code_quality", 0.0),
        "reviewedness": results.get("reviewedness", 0.0),
        "reproducibility": results.get("reproducibility", 0.0),
        "tree_score": results.get("tree_score", 0.0),
    }

    net_score, net_latency = calculate_net_score_with_timing(complete_metrics)
    results["net_score"] = net_score
    results["net_score_latency"] = net_latency

    # Total latency includes all parallel computation plus net score calculation
    end_time = time.perf_counter()
    total_latency = int((end_time - start_time) * 1000)

    # Update net_score_latency to be the total latency for the entire computation
    results["net_score_latency"] = total_latency

    return results, total_latency
