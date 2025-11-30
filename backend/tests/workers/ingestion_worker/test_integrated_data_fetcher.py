"""Tests for integrated_data_fetcher.py module."""

from typing import Any, Dict
from unittest.mock import Mock

from app.workers.ingestion_worker.src.integrated_data_fetcher import (
    IntegratedDataFetcher,
)
from app.workers.ingestion_worker.src.log import loggerInstance
from app.workers.ingestion_worker.src.log.logger import Logger

loggerInstance.logger = Logger()


class TestIntegratedDataFetcherInit:
    """Tests for IntegratedDataFetcher initialization."""

    def test_init_with_no_tokens(self) -> None:
        """Test initialization without tokens."""
        fetcher = IntegratedDataFetcher()
        assert fetcher.hf_api_token is None or fetcher.hf_api_token == ""
        assert fetcher.github_token is None or fetcher.github_token == ""
        assert fetcher.hf_headers == {}
        assert fetcher.gh_headers == {}

    def test_init_with_tokens(self) -> None:
        """Test initialization with tokens."""
        fetcher = IntegratedDataFetcher(
            hf_api_token="hf_token", github_token="gh_token"
        )
        assert fetcher.hf_api_token == "hf_token"
        assert fetcher.github_token == "gh_token"
        assert "Authorization" in fetcher.hf_headers
        assert "Authorization" in fetcher.gh_headers


class TestExtractMethods:
    """Tests for URL extraction methods."""

    def test_extract_hf_model_id(self) -> None:
        """Test extracting Hugging Face model ID."""
        fetcher = IntegratedDataFetcher()

        url = "https://huggingface.co/google/bert-base"
        model_id = fetcher._extract_hf_model_id(url)
        assert model_id == "google/bert-base"

    def test_extract_hf_model_id_invalid(self) -> None:
        """Test extracting model ID from invalid URL."""
        fetcher = IntegratedDataFetcher()

        url = "https://invalid.com"
        model_id = fetcher._extract_hf_model_id(url)
        assert model_id is None

    def test_extract_hf_dataset_id(self) -> None:
        """Test extracting Hugging Face dataset ID."""
        fetcher = IntegratedDataFetcher()

        url = "https://huggingface.co/datasets/squad"
        dataset_id = fetcher._extract_hf_dataset_id(url)
        assert dataset_id == "squad"

    def test_extract_hf_dataset_id_with_org(self) -> None:
        """Test extracting dataset ID with organization."""
        fetcher = IntegratedDataFetcher()

        url = "https://huggingface.co/datasets/google/test"
        dataset_id = fetcher._extract_hf_dataset_id(url)
        assert dataset_id == "google/test"

    def test_extract_github_repo(self) -> None:
        """Test extracting GitHub repository info."""
        fetcher = IntegratedDataFetcher()

        url = "https://github.com/user/repo"
        repo_info = fetcher._extract_github_repo(url)
        assert repo_info == ("user", "repo")

    def test_extract_github_repo_invalid(self) -> None:
        """Test extracting repo info from invalid URL."""
        fetcher = IntegratedDataFetcher()

        url = "https://invalid.com"
        repo_info = fetcher._extract_github_repo(url)
        assert repo_info is None


class TestLicenseExtraction:
    """Tests for license extraction."""

    def test_extract_license_from_tags(self) -> None:
        """Test extracting license from tags."""
        fetcher = IntegratedDataFetcher()

        info_dict: Dict[str, Any] = {"tags": ["license:mit", "python"]}
        license_val = fetcher._extract_license_from_tags(info_dict)
        assert license_val == "mit"

    def test_extract_license_from_direct_field(self) -> None:
        """Test extracting license from direct field."""
        fetcher = IntegratedDataFetcher()

        info_dict: Dict[str, Any] = {"license": "apache-2.0"}
        license_val = fetcher._extract_license_from_tags(info_dict)
        assert license_val == "apache-2.0"

    def test_extract_license_from_readme(self) -> None:
        """Test extracting license from README."""
        fetcher = IntegratedDataFetcher()

        info_dict: Dict[str, Any] = {}
        readme = "# Model\n\nlicense: MIT\n"
        license_val = fetcher._extract_license_from_tags(info_dict, readme)
        assert license_val.lower() == "mit"

    def test_extract_license_not_found(self) -> None:
        """Test license extraction when not found."""
        fetcher = IntegratedDataFetcher()

        info_dict: Dict[str, Any] = {}
        license_val = fetcher._extract_license_from_tags(info_dict)
        assert license_val == ""

    def test_extract_license_multiple_tags(self) -> None:
        """Test extracting license when multiple license tags exist."""
        fetcher = IntegratedDataFetcher()

        info_dict: Dict[str, Any] = {"tags": ["python", "license:apache-2.0", "ml"]}
        license_val = fetcher._extract_license_from_tags(info_dict)
        assert license_val == "apache-2.0"

    def test_extract_license_from_tags_with_non_string(self) -> None:
        """Test extracting license when tags contain non-strings."""
        fetcher = IntegratedDataFetcher()

        info_dict: Dict[str, Any] = {"tags": [123, "license:gpl", None]}
        license_val = fetcher._extract_license_from_tags(info_dict)
        assert license_val == "gpl"


class TestAPIHelpers:
    """Tests for API helper methods."""

    def test_get_hf_model_info_success(self) -> None:
        """Test successful model info retrieval."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.json.return_value = {"downloads": 1000}
        mock_response.raise_for_status.return_value = None
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_hf_model_info("google/bert")

        assert result == {"downloads": 1000}

    def test_get_hf_model_info_failure(self) -> None:
        """Test failed model info retrieval."""
        fetcher = IntegratedDataFetcher()
        fetcher.session = Mock()
        fetcher.session.get.side_effect = Exception("Network error")

        result = fetcher._get_hf_model_info("google/bert")

        assert result == {}

    def test_get_github_repo_info_success(self) -> None:
        """Test successful GitHub repo info retrieval."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.json.return_value = {"stars": 1000}
        mock_response.raise_for_status.return_value = None
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_github_repo_info("user", "repo")

        assert result == {"stars": 1000}

    def test_get_github_readme_success(self) -> None:
        """Test successful README retrieval."""
        import base64

        readme_content = "# Test Repo"
        encoded_content = base64.b64encode(readme_content.encode()).decode()

        fetcher = IntegratedDataFetcher()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": encoded_content}
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_github_readme("user", "repo")

        assert result == readme_content

    def test_get_github_readme_not_found(self) -> None:
        """Test README not found."""
        fetcher = IntegratedDataFetcher()
        mock_response = Mock()
        mock_response.status_code = 404
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_github_readme("user", "repo")

        assert result == ""

    def test_get_hf_model_files_success(self) -> None:
        """Test successful model files retrieval."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.json.return_value = [
            {"path": "config.json", "size": 1024, "type": "file"},
            {"path": "pytorch_model.bin", "size": 5000000, "type": "file"},
        ]
        mock_response.raise_for_status.return_value = None
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_hf_model_files("google/bert")

        assert "config.json" in result
        assert "pytorch_model.bin" in result

    def test_get_hf_model_files_failure(self) -> None:
        """Test failed model files retrieval."""
        fetcher = IntegratedDataFetcher()
        fetcher.session = Mock()
        fetcher.session.get.side_effect = Exception("Network error")

        result = fetcher._get_hf_model_files("google/bert")
        assert result == {}

    def test_get_hf_readme_success(self) -> None:
        """Test successful HF README retrieval."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Model Card"
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_hf_readme("google/bert")
        assert result == "# Model Card"

    def test_get_hf_readme_not_found(self) -> None:
        """Test HF README not found."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.status_code = 404
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_hf_readme("google/bert")
        assert result == ""

    def test_get_hf_readme_exception(self) -> None:
        """Test HF README with exception."""
        fetcher = IntegratedDataFetcher()
        fetcher.session = Mock()
        fetcher.session.get.side_effect = Exception("Network error")

        result = fetcher._get_hf_readme("google/bert")
        assert result == ""

    def test_get_hf_dataset_info_success(self) -> None:
        """Test successful dataset info retrieval."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.json.return_value = {"downloads": 5000}
        mock_response.raise_for_status.return_value = None
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_hf_dataset_info("squad")
        assert result["downloads"] == 5000

    def test_get_hf_dataset_info_failure(self) -> None:
        """Test failed dataset info retrieval."""
        fetcher = IntegratedDataFetcher()
        fetcher.session = Mock()
        fetcher.session.get.side_effect = Exception("Network error")

        result = fetcher._get_hf_dataset_info("squad")
        assert result == {}

    def test_get_hf_dataset_files_success(self) -> None:
        """Test successful dataset files retrieval."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.json.return_value = [
            {"path": "data.csv", "size": 2048, "type": "file"}
        ]
        mock_response.raise_for_status.return_value = None
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_hf_dataset_files("squad")
        assert "data.csv" in result

    def test_get_hf_dataset_files_failure(self) -> None:
        """Test failed dataset files retrieval."""
        fetcher = IntegratedDataFetcher()
        fetcher.session = Mock()
        fetcher.session.get.side_effect = Exception("Network error")

        result = fetcher._get_hf_dataset_files("squad")
        assert result == {}

    def test_get_hf_dataset_readme_success(self) -> None:
        """Test successful dataset README retrieval."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Dataset Card"
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_hf_dataset_readme("squad")
        assert result == "# Dataset Card"

    def test_get_hf_dataset_readme_not_found(self) -> None:
        """Test dataset README not found."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.status_code = 404
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_hf_dataset_readme("squad")
        assert result == ""

    def test_get_hf_dataset_readme_exception(self) -> None:
        """Test dataset README with exception."""
        fetcher = IntegratedDataFetcher()
        fetcher.session = Mock()
        fetcher.session.get.side_effect = Exception("Network error")

        result = fetcher._get_hf_dataset_readme("squad")
        assert result == ""

    def test_get_github_contributors_success(self) -> None:
        """Test successful contributors retrieval."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"login": "user1"}, {"login": "user2"}]
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_github_contributors("user", "repo")
        assert result == ["user1", "user2"]

    def test_get_github_contributors_not_found(self) -> None:
        """Test contributors not found."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.status_code = 404
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_github_contributors("user", "repo")
        assert result == []

    def test_get_github_contributors_exception(self) -> None:
        """Test contributors with exception."""
        fetcher = IntegratedDataFetcher()
        fetcher.session = Mock()
        fetcher.session.get.side_effect = Exception("Network error")

        result = fetcher._get_github_contributors("user", "repo")
        assert result == []

    def test_get_github_recent_commits_success(self) -> None:
        """Test successful recent commits retrieval."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"sha": "abc123"}, {"sha": "def456"}]
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_github_recent_commits("user", "repo")
        assert len(result) == 2

    def test_get_github_recent_commits_not_found(self) -> None:
        """Test recent commits not found."""
        fetcher = IntegratedDataFetcher()

        mock_response = Mock()
        mock_response.status_code = 404
        fetcher.session = Mock()
        fetcher.session.get.return_value = mock_response

        result = fetcher._get_github_recent_commits("user", "repo")
        assert result == []

    def test_get_github_recent_commits_exception(self) -> None:
        """Test recent commits with exception."""
        fetcher = IntegratedDataFetcher()
        fetcher.session = Mock()
        fetcher.session.get.side_effect = Exception("Network error")

        result = fetcher._get_github_recent_commits("user", "repo")
        assert result == []


class TestContributorsExtraction:
    """Tests for contributors extraction."""

    def test_extract_contributors_with_author(self) -> None:
        """Test extracting contributors when author present."""
        fetcher = IntegratedDataFetcher()

        info: Dict[str, Any] = {"author": "google"}
        result = fetcher._extract_contributors(info, "google/bert")
        assert result == ["google"]

    def test_extract_contributors_without_author(self) -> None:
        """Test extracting contributors using fallback."""
        fetcher = IntegratedDataFetcher()

        info: Dict[str, Any] = {}
        result = fetcher._extract_contributors(info, "google/bert")
        assert result == ["google"]

    def test_extract_contributors_with_empty_author(self) -> None:
        """Test extracting contributors with empty author field."""
        fetcher = IntegratedDataFetcher()

        info: Dict[str, Any] = {"author": ""}
        result = fetcher._extract_contributors(info, "openai/gpt3")
        assert result == ["openai"]


class TestGitHubLicenseExtraction:
    """Tests for GitHub license extraction."""

    def test_extract_github_license_present(self) -> None:
        """Test extracting license when present."""
        fetcher = IntegratedDataFetcher()

        repo_data: Dict[str, Any] = {"license": {"spdx_id": "MIT"}}
        result = fetcher._extract_github_license(repo_data)
        assert result == "MIT"

    def test_extract_github_license_missing(self) -> None:
        """Test extracting license when missing."""
        fetcher = IntegratedDataFetcher()

        repo_data: Dict[str, Any] = {}
        result = fetcher._extract_github_license(repo_data)
        assert result == ""

    def test_extract_github_license_null(self) -> None:
        """Test extracting license when null."""
        fetcher = IntegratedDataFetcher()

        repo_data: Dict[str, Any] = {"license": None}
        result = fetcher._extract_github_license(repo_data)
        assert result == ""

    def test_extract_github_license_with_different_keys(self) -> None:
        """Test extracting license with various data structures."""
        fetcher = IntegratedDataFetcher()

        # Test with spdx_id
        repo_data = {"license": {"spdx_id": "Apache-2.0", "name": "Apache"}}
        result = fetcher._extract_github_license(repo_data)
        assert result == "Apache-2.0"

        # Test with missing spdx_id
        repo_data = {"license": {"name": "MIT"}}
        result = fetcher._extract_github_license(repo_data)
        assert result == ""
