"""Entry points and helpers for running the rate worker CLI."""

import json
import os
import sys
import time
from typing import Any, Dict, Optional

import requests

from .log import loggerInstance
from .log.logger import Logger
from .scorer import ScoreResult, score_url
from .url import Url, UrlCategory, UrlSet

# Disable huggingface_hub progress bars globally
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def format_floats_to_2dp(obj):
    """Recursively format all float values to 2 decimal places."""
    if isinstance(obj, dict):
        return {k: format_floats_to_2dp(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [format_floats_to_2dp(item) for item in obj]
    elif isinstance(obj, float):
        return round(obj, 2)
    else:
        return obj


def validate_github_token() -> bool:
    """Validate GitHub token if provided.

    Returns:
        True if token is valid or not provided (will use rate-limited access)
        False if token is provided but invalid
    """
    github_token = os.getenv("GITHUB_TOKEN", "")

    if not github_token:
        # No token provided - will use rate-limited access
        loggerInstance.logger.log_info(
            "No GITHUB_TOKEN provided, using rate-limited API access"
        )
        return True

    # Validate the token by making a test request
    try:
        response = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {github_token}"},
            timeout=5,
        )

        if response.status_code == 200:
            loggerInstance.logger.log_info("GitHub token validated successfully")
            return True
        elif response.status_code == 401:
            loggerInstance.logger.log_info("Invalid GITHUB_TOKEN detected")
            return False
        else:
            # Other errors - continue with caution
            loggerInstance.logger.log_info(
                f"GitHub token validation returned status {response.status_code}"
            )
            return True
    except Exception:
        # Network error or other issue - continue anyway
        return True


def validate_log_file() -> bool:
    """Validate log file path if provided.

    Returns:
        True if log file path is valid
        False if log file path is invalid or cannot be created
    """
    log_file_path = os.getenv("LOG_FILE", "")

    if not log_file_path:
        return False

    try:
        from pathlib import Path

        # Get the directory path
        log_path = Path(log_file_path)
        # The log file must already exist, according to an instructor note on Piazza
        if not log_path.exists():
            # print(f"Error: Log file does not exist: {log_path}")
            return False
        log_dir = log_path.parent

        # Don't try to create nested directories that don't exist
        if not log_dir.exists():
            # Check if parent directory exists - if not, we can't create nested
            if not log_dir.parent.exists():
                return False
            try:
                log_dir.mkdir(exist_ok=True)
            except Exception:
                return False

        if not os.access(log_dir, os.W_OK):
            return False

        # Try to append to the log file
        try:
            f = open(log_file_path, "a")  # Just test if we can open it
            return True
        except Exception:
            return False
        finally:
            f.close()

    except Exception:
        # print(f"Error: Invalid log file path: {log_file_path}", file=sys.stderr)
        # print(f"Reason: {e}", file=sys.stderr)
        return False


def parseUrlFile(urlFile: str) -> list[UrlSet]:
    """Parse URL file in CSV format: code_url,dataset_url,model_url.

    Each line can contain up to 3 URLs separated by commas.
    Empty fields are represented by empty strings between commas.
    Example: ,,model_url means only model URL is provided.
    """
    f = open(urlFile, "r")
    urlset_list: list[UrlSet] = list()

    lines: list[str] = f.read().strip().split("\n")
    for line in lines:
        if line.strip() == "":  # Skip empty lines
            continue

        # Split by comma to get individual URLs
        urls_in_line = line.split(",")

        # Code and dataset URL can be empty
        code_url: Optional[Url] = (
            Url(urls_in_line[0].strip()) if len(urls_in_line[0]) > 0 else None
        )
        dataset_url: Optional[Url] = (
            Url(urls_in_line[1].strip()) if len(urls_in_line[1]) > 0 else None
        )
        model_url: Url = Url(urls_in_line[2].strip())
        urlset_list.append(UrlSet(code_url, dataset_url, model_url))

    #        # Process each URL in the line
    #        for url_string in urls_in_line:
    #            url_string = url_string.strip()
    #            if url_string:  # Only add non-empty URLs
    #                url_list.append(Url(url_string))

    f.close()
    return urlset_list


def calculate_scores(urlset: UrlSet) -> Dict[str, Any]:
    """Calculate and return trustworthiness scores for a single UrlSet."""
    total_score = 0.0
    total_max_score = 0.0
    valid_urls = 0
    result_entry: Optional[Dict[str, Any]] = None

    code: Optional[Url] = urlset.code
    model: Url = urlset.model
    if model.category == UrlCategory.INVALID:
        start_time = time.perf_counter()
        net_score = 0.0
        end_time = time.perf_counter()
        net_score_latency = round(
            (end_time - start_time) * 1000
        )  # Convert to milliseconds and round
        result_entry = {
            "name": "unknown",
            "category": "INVALID",
            "net_score": net_score,
            "net_score_latency": net_score_latency,
            "ramp_up_time": 0.0,
            "ramp_up_time_latency": 0,
            "bus_factor": 0.0,
            "bus_factor_latency": 0,
            "performance_claims": 0.0,
            "performance_claims_latency": 0,
            "license": 0.0,
            "license_latency": 0,
            "size_score": {
                "raspberry_pi": 0.0,
                "jetson_nano": 0.0,
                "desktop_pc": 0.0,
                "aws_server": 0.0,
            },
            "size_score_latency": 0,
            "dataset_and_code_score": 0.0,
            "dataset_and_code_score_latency": 0,
            "dataset_quality": 0.0,
            "dataset_quality_latency": 0,
            "code_quality": 0.0,
            "code_quality_latency": 0,
            "error": "Invalid URL - Not a dataset, model, or code URL",
        }
    else:
        code_url = code.link if code else None
        modelResultOptional: Optional[ScoreResult] = score_url(
            model.link, model.category, code_url
        )
        if modelResultOptional is None:
            raise Exception("Model can't be scored")
        else:
            modelResult: ScoreResult = modelResultOptional

        if modelResult.score > 0:
            if modelResult.details.get("downloads", 0) > 0:
                loggerInstance.logger.log_info(
                    f"     - Downloads: {modelResult.details['downloads']:,}"
                )
            if modelResult.details.get("likes", 0) > 0:
                loggerInstance.logger.log_info(
                    f"     - Likes: {modelResult.details['likes']}"
                )
            if modelResult.details.get("has_model_card"):
                loggerInstance.logger.log_info("     - Has Model Card: ")
            if modelResult.details.get("pipeline_tag"):
                loggerInstance.logger.log_info(
                    f"     - Pipeline Tag: {modelResult.details['pipeline_tag']}"
                )

            total_score += modelResult.score
            total_max_score += modelResult.max_score
            valid_urls += 1

            net_score = modelResult.details.get("net_score", 0.0)
            net_score_latency = modelResult.details.get("net_score_latency", 0)

            result_entry = {
                "name": modelResult.details.get("name", "unknown").split("/")[
                    -1
                ],  # Just model name
                "category": model.category.name,
                "net_score": round(net_score, 2),
                "net_score_latency": net_score_latency,
                "ramp_up_time": round(modelResult.details.get("ramp_up_time", 0.5), 2),
                "ramp_up_time_latency": modelResult.details.get(
                    "ramp_up_time_latency", 30
                ),
                "bus_factor": round(modelResult.details.get("bus_factor", 0.0), 2),
                "bus_factor_latency": modelResult.details.get("bus_factor_latency", 20),
                "performance_claims": round(
                    modelResult.details.get("performance_claims", 0.5), 2
                ),
                "performance_claims_latency": modelResult.details.get(
                    "performance_claims_latency", 30
                ),
                "license": round(modelResult.details.get("license", 0.5), 2),
                "license_latency": modelResult.details.get("license_latency", 10),
                "size_score": {
                    k: round(v, 2)
                    for k, v in modelResult.details.get("size_score", {}).items()
                },
                "size_score_latency": modelResult.details.get("size_score_latency", 40),
                "dataset_and_code_score": round(
                    modelResult.details.get("dataset_and_code_score", 0.5), 2
                ),
                "dataset_and_code_score_latency": modelResult.details.get(
                    "dataset_and_code_score_latency", 15
                ),
                "dataset_quality": round(
                    modelResult.details.get("dataset_quality", 0.5), 2
                ),
                "dataset_quality_latency": modelResult.details.get(
                    "dataset_quality_latency", 20
                ),
                "code_quality": round(modelResult.details.get("code_quality", 0.5), 2),
                "code_quality_latency": modelResult.details.get(
                    "code_quality_latency", 20
                ),
            }
        else:
            start_time = time.perf_counter()
            net_score = 0.0
            end_time = time.perf_counter()
            net_score_latency = round(
                (end_time - start_time) * 1000
            )  # Convert to milliseconds and round

            result_entry = {
                "name": modelResult.details.get("name", "unknown"),
                "category": model.category.name,
                "net_score": net_score,
                "net_score_latency": net_score_latency,
                "ramp_up_time": 0.0,
                "ramp_up_time_latency": 0,
                "bus_factor": 0.0,
                "bus_factor_latency": 0,
                "performance_claims": 0.0,
                "performance_claims_latency": 0,
                "license": 0.0,
                "license_latency": 0,
                "size_score": modelResult.details.get("size_score", {}),
                "size_score_latency": 0,
                "dataset_and_code_score": 0.0,
                "dataset_and_code_score_latency": 0,
                "dataset_quality": 0.0,
                "dataset_quality_latency": 0,
                "code_quality": 0.0,
                "code_quality_latency": 0,
                "error": modelResult.details.get("error", "Failed to score"),
            }

    formatted_entry = format_floats_to_2dp(result_entry) if result_entry else {}
    return formatted_entry


def main() -> int:
    """Command-line entry for processing URL files and scoring artifacts."""
    # Validate log file path if provided
    if not validate_log_file():
        return 1

    loggerInstance.logger = Logger()

    # Validate GitHub token if provided
    if not validate_github_token():
        return 1

    if (len(sys.argv)) != 2:
        return 1

    urlFile = sys.argv[1]
    urls: list[UrlSet] = parseUrlFile(urlFile)
    for url in urls:
        pass

    for urlset in urls:
        ndjson_output = calculate_scores(urlset)
        formatted_output = json.dumps(ndjson_output, separators=(",", ":")).replace(
            " ", ""
        )
        sys.stdout.write(formatted_output + "\n")

    return 0


if __name__ == "__main__":
    return_code: int = main()
    sys.exit(return_code)


# from .url import Url, UrlCategory, UrlSet
# from .scorer import score_url, ScoreResult
# import sys
# import json
# import time
# import os
# import requests
# from typing import List, Dict, Any, Optional
# from .log.logger import Logger
# from .log import loggerInstance

# # Disable huggingface_hub progress bars globally
# os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
# os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


# def format_floats_to_2dp(obj):
#     """Recursively format all float values to 2 decimal places"""
#     if isinstance(obj, dict):
#         return {k: format_floats_to_2dp(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [format_floats_to_2dp(item) for item in obj]
#     elif isinstance(obj, float):
#         return round(obj, 2)
#     else:
#         return obj


# def validate_github_token() -> bool:
#     """Validate GitHub token if provided.

#     Returns:
#         True if token is valid or not provided (will use rate-limited access)
#         False if token is provided but invalid
#     """
#     github_token = os.getenv("GITHUB_TOKEN", "")

#     if not github_token:
#         # No token provided - will use rate-limited access
#         return True

#     # Validate the token by making a test request
#     try:
#         response = requests.get(
#             "https://api.github.com/user",
#             headers={"Authorization": f"token {github_token}"},
#             timeout=5
#         )

#         if response.status_code == 200:
#             return True
#         elif response.status_code == 401:
#             return False
#         else:
#             # Other errors - continue with caution
#             return True
#     except Exception as e:
#         # Network error or other issue - continue anyway
#         return True


# def validate_log_file() -> bool:
#     """Validate log file path if provided.

#     Returns:
#         True if log file path is valid
#         False if log file path is invalid or cannot be created
#     """
#     log_file_path = os.getenv("LOG_FILE", "")

#     if not log_file_path:
#         return False

#     try:
#         from pathlib import Path

#         # Get the directory path
#         log_path = Path(log_file_path)
#         # The log file must already exist, according to an instructor note on Piazza
#         if not log_path.exists():
#             # print(f"Error: Log file does not exist: {log_path}")
#             return False
#         log_dir = log_path.parent

#         # Don't try to create nested directories that don't exist
#         if not log_dir.exists():
#             # Check if parent directory exists - if not, we can't create nested
#             if not log_dir.parent.exists():
#                 return False
#             try:
#                 log_dir.mkdir(exist_ok=True)
#             except Exception as e:
#                 # print(f"Reason: {e}", file=sys.stderr)
#                 return False

#         if not os.access(log_dir, os.W_OK):
#             return False


#         # Try to append to the log file
#         try:
#             with open(log_file_path, "a") as f:
#                 pass  # Just test if we can open it
#             return True
#         except Exception as e:
#             # print(f"Reason: {e}", file=sys.stderr)
#             return False

#     except Exception as e:
#         # print(f"Error: Invalid log file path: {log_file_path}", file=sys.stderr)
#         # print(f"Reason: {e}", file=sys.stderr)
#         return False


# def parseUrlFile(urlFile: str) -> list[UrlSet]:
#     """Parse URL file in CSV format: code_url,dataset_url,model_url

#     Each line can contain up to 3 URLs separated by commas.
#     Empty fields are represented by empty strings between commas.
#     Example: ,,model_url means only model URL is provided.
#     """
#     f = open(urlFile, "r")
#     urlset_list: list[UrlSet] = list()

#     lines: list[str] = f.read().strip().split("\n")
#     for line in lines:
#         if line.strip() == "":  # Skip empty lines
#             continue

#         # Split by comma to get individual URLs
#         urls_in_line = line.split(",")

#         # Code and dataset URL can be empty
#         model_url : Url = Url(urls_in_line[2].strip())
#         urlset_list.append(UrlSet(code_url, dataset_url, model_url))

# #        # Process each URL in the line
# #        for url_string in urls_in_line:
# #            url_string = url_string.strip()
# #            if url_string:  # Only add non-empty URLs
# #                url_list.append(Url(url_string))

#     f.close()
#     return urlset_list


# def calculate_scores(urlsets: list[UrlSet]) -> None:
#     """Calculate and display trustworthiness scores for URLs."""


#     total_score = 0.0
#     total_max_score = 0.0
#     valid_urls = 0
#     ndjson_results: List[Dict[str, Any]] = []

#     for urlset in urlsets:
#         code:Optional[Url] = urlset.code
#         dataset: Optional[Url] = urlset.dataset
#         model:Url = urlset.model
#         if model.category == UrlCategory.INVALID:
#             # Add to NDJSON even for invalid URLs
#             # Measure net_score calculation latency for invalid URLs (should be 0)
#             start_time = time.perf_counter()
#             net_score = 0.0
#             end_time = time.perf_counter()
#             net_score_latency = round(
#                 (end_time - start_time) * 1000
#             )  # Convert to milliseconds and round
#             ndjson_results.append(
#                 {
#                     "name": "unknown",
#                     "category": "INVALID",
#                     "net_score": net_score,
#                     "net_score_latency": net_score_latency,
#                     "ramp_up_time": 0.0,
#                     "ramp_up_time_latency": 0,
#                     "bus_factor": 0.0,
#                     "bus_factor_latency": 0,
#                     "performance_claims": 0.0,
#                     "performance_claims_latency": 0,
#                     "license": 0.0,
#                     "license_latency": 0,
#                     "size_score_latency": 0,
#                     "dataset_and_code_score": 0.0,
#                     "dataset_and_code_score_latency": 0,
#                     "dataset_quality": 0.0,
#                     "dataset_quality_latency": 0,
#                     "code_quality": 0.0,
#                     "code_quality_latency": 0,
#                     "error": "Invalid URL - Not a dataset, model, or code URL",
#                 }
#             )

#             continue


#             if modelResult.details.get("has_model_card"):
#             if modelResult.details.get("pipeline_tag"):
# #
# #            elif url.category == UrlCategory.CODE:
# #                if result.details.get("stars", 0) > 0:
# #                if result.details.get("forks", 0) > 0:
# #                if result.details.get("has_description"):
# #                if result.details.get("has_license"):
# #                if result.details.get("language"):

#             # Add to totals
#             total_score += modelResult.score
#             total_max_score += modelResult.max_score
#             valid_urls += 1

#             # Add to NDJSON results
#                     "net_score": net_score,
#                     "net_score_latency": net_score_latency,
#                     "ramp_up_time": 0.0,
#                     "ramp_up_time_latency": 0,
#                     "bus_factor": 0.0,
#                     "bus_factor_latency": 0,
#                     "performance_claims": 0.0,
#                     "performance_claims_latency": 0,
#                     "license": 0.0,
#                     "license_latency": 0,
#                     "size_score": modelResult.details.get("size_score", {}),
#                     "size_score_latency": 0,
#                     "dataset_and_code_score": 0.0,
#                     "dataset_and_code_score_latency": 0,
#                     "dataset_quality": 0.0,
#                     "dataset_quality_latency": 0,
#                     "code_quality": 0.0,
#                     "code_quality_latency": 0,
#                     "error": modelResult.details.get("error", "Failed to score"),
#                 }
#             )

#     # Display summary
#     import sys

#     return_code: int = main()
#     sys.exit(return_code)
