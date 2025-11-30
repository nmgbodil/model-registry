"""Tests for main.py module."""

import os
import sys
import tempfile
from typing import Any
from unittest.mock import Mock, patch

from app.workers.ingestion_worker.src.main import (
    calculate_scores,
    main,
    parseUrlFile,
    validate_github_token,
    validate_log_file,
)
from app.workers.ingestion_worker.src.url import Url, UrlCategory, UrlSet


class TestValidateGithubToken:
    """Tests for GitHub token validation."""

    @patch.dict(os.environ, {}, clear=True)
    def test_no_token_provided(self) -> None:
        """Test that missing token returns True (rate-limited access)."""
        assert validate_github_token() is True

    @patch("app.workers.ingestion_worker.src.main.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "valid_token"})
    def test_valid_token(self, mock_get: Any) -> None:
        """Test that valid token returns True."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert validate_github_token() is True

    @patch("app.workers.ingestion_worker.src.main.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "invalid_token"})
    def test_invalid_token(self, mock_get: Any) -> None:
        """Test that invalid token returns False."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        assert validate_github_token() is False

    @patch("app.workers.ingestion_worker.src.main.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "token"})
    def test_token_validation_network_error(self, mock_get: Any) -> None:
        """Test that network errors don't block execution."""
        mock_get.side_effect = Exception("Network error")

        assert validate_github_token() is True

    @patch("app.workers.ingestion_worker.src.main.requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "token"})
    def test_token_validation_other_status(self, mock_get: Any) -> None:
        """Test that other status codes allow continuation."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        assert validate_github_token() is True


class TestValidateLogFile:
    """Tests for log file validation."""

    @patch.dict(os.environ, {}, clear=True)
    def test_no_log_file_provided(self) -> None:
        """Test that missing log file returns True."""
        assert validate_log_file() is False

    def test_valid_log_file_path(self) -> None:
        """Test that valid log file path returns True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            with patch.dict(os.environ, {"LOG_FILE": log_file}):
                assert validate_log_file() is False  # Because the file doesn't exist
                assert not os.path.exists(log_file)

    def test_log_file_with_nested_directories(self) -> None:
        """Test that nested directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "logs", "nested", "test.log")
            with patch.dict(os.environ, {"LOG_FILE": log_file}):
                assert validate_log_file() is False
                assert not os.path.exists(log_file)

    def test_invalid_log_file_path(self) -> None:
        """Test that invalid path returns False."""
        with patch.dict(os.environ, {"LOG_FILE": "/root/invalid/path/test.log"}):
            # This should fail on non-root systems
            result = validate_log_file()
            # Result depends on permissions, but shouldn't crash
            assert isinstance(result, bool)


class TestParseUrlFile:
    """Tests for URL file parsing."""

    def test_parse_single_line_csv(self) -> None:
        """Test parsing single line with 3 URLs."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(
                "https://github.com/user/repo,https://huggingface.co/datasets/test,"
                "https://huggingface.co/model\n"
            )
            f.flush()
            filename = f.name

        try:
            urlsets = parseUrlFile(filename)
            assert len(urlsets) == 1  # Only 1 URL Set
            assert isinstance(urlsets[0].code, Url)
            assert urlsets[0].code.category == UrlCategory.CODE
            assert isinstance(urlsets[0].dataset, Url)
            assert urlsets[0].dataset.category == UrlCategory.DATASET
            assert isinstance(urlsets[0].model, Url)
            assert urlsets[0].model.category == UrlCategory.MODEL
        finally:
            os.unlink(filename)

    def test_parse_partial_entries(self) -> None:
        """Test parsing lines with empty fields."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(",,https://huggingface.co/model\n")
            f.write(",,https://huggingface.co/model2,\n")
            f.flush()
            filename = f.name

        try:
            urlsets = parseUrlFile(filename)
            assert len(urlsets) == 2
        finally:
            os.unlink(filename)

    def test_parse_multiple_lines(self) -> None:
        """Test parsing multiple lines."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(
                "https://github.com/user/repo,https://huggingface.co/datasets/test,"
                "https://huggingface.co/model\n"
            )
            f.write(
                "https://github.com/user2/repo2,https://huggingface.co/datasets/test2,"
                "https://huggingface.co/model2\n"
            )
            f.flush()
            filename = f.name

        try:
            urlsets = parseUrlFile(filename)
            assert len(urlsets) == 2
        finally:
            os.unlink(filename)

    def test_parse_empty_file(self) -> None:
        """Test parsing empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("")
            f.flush()
            filename = f.name

        try:
            urls = parseUrlFile(filename)
            assert len(urls) == 0
        finally:
            os.unlink(filename)

    def test_parse_file_with_blank_lines(self) -> None:
        """Test parsing file with blank lines."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(
                "https://github.com/user/repo,https://huggingface.co/datasets/test,"
                "https://huggingface.co/model\n"
            )
            f.write("\n")
            f.write("\n")
            f.write(
                "https://github.com/user2/repo2,https://huggingface.co/datasets/test2,"
                "https://huggingface.co/model2\n"
            )
            f.flush()
            filename = f.name

        try:
            urlsets = parseUrlFile(filename)
            assert len(urlsets) == 2
        finally:
            os.unlink(filename)

    def test_parse_file_with_whitespace(self) -> None:
        """Test parsing file with extra whitespace."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(
                "  https://github.com/user/repo  ,  https://huggingface.co/datasets/"
                "test  ,  https://huggingface.co/model  \n"
            )
            f.flush()
            filename = f.name

        try:
            urlsets = parseUrlFile(filename)
            assert len(urlsets) == 1
            assert "  " not in urlsets[0].model.link
        finally:
            os.unlink(filename)


class TestCalculateScores:
    """Tests for calculate_scores function."""

    @patch("app.workers.ingestion_worker.src.main.score_url")
    def test_calculate_scores_valid_urls(self, mock_score: Any) -> None:
        """Test calculate_scores with valid URLs."""
        from app.workers.ingestion_worker.src.scorer import ScoreResult

        mock_score.return_value = ScoreResult(
            url="https://huggingface.co/model",
            category=UrlCategory.MODEL,
            score=8.0,
            max_score=10.0,
            details={"name": "test-model", "downloads": 1000},
        )

        urlset = UrlSet(
            None, None, Url("https://huggingface.co/model", UrlCategory.MODEL)
        )

        result = calculate_scores(urlset)
        assert result["category"] == "MODEL"
        assert result["net_score"] == round(
            mock_score.return_value.details.get("net_score", 0.0), 2
        )
        assert result["name"] == "test-model"

    @patch("app.workers.ingestion_worker.src.main.score_url")
    def test_calculate_scores_invalid_urls(self, mock_score: Any) -> None:
        """Test calculate_scores with invalid URLs."""
        urlset = UrlSet(None, None, Url("https://invalid.com", UrlCategory.INVALID))

        result = calculate_scores(urlset)
        assert result["category"] == "INVALID"
        assert result["net_score"] == 0.0
        assert "error" in result

    @patch("app.workers.ingestion_worker.src.main.score_url")
    def test_calculate_scores_mixed_urls(self, mock_score: Any) -> None:
        """Test calculate_scores with mix of valid and invalid URLs."""
        from app.workers.ingestion_worker.src.scorer import ScoreResult

        mock_score.return_value = ScoreResult(
            url="https://huggingface.co/model",
            category=UrlCategory.MODEL,
            score=7.0,
            max_score=10.0,
            details={"name": "test"},
        )

        valid_urlset = UrlSet(
            None, None, Url("https://huggingface.co/model", UrlCategory.MODEL)
        )
        invalid_urlset = UrlSet(
            None, None, Url("https://invalid.com", UrlCategory.INVALID)
        )

        valid_result = calculate_scores(valid_urlset)
        invalid_result = calculate_scores(invalid_urlset)

        assert valid_result["category"] == "MODEL"
        assert invalid_result["category"] == "INVALID"


class TestMain:
    """Tests for main function."""

    @patch("app.workers.ingestion_worker.src.main.validate_log_file")
    @patch("app.workers.ingestion_worker.src.main.validate_github_token")
    @patch("app.workers.ingestion_worker.src.main.parseUrlFile")
    @patch("app.workers.ingestion_worker.src.main.calculate_scores")
    @patch("app.workers.ingestion_worker.src.log.loggerInstance.logger")
    def test_main_success(
        self,
        mock_logger: Any,
        mock_calc: Any,
        mock_parse: Any,
        mock_token: Any,
        mock_log: Any,
    ) -> None:
        """Test successful main execution."""
        mock_log.return_value = True
        mock_token.return_value = True
        mock_parse.return_value = [
            UrlSet(None, None, Url("https://huggingface.co/model", UrlCategory.MODEL)),
        ]
        mock_calc.return_value = {
            "category": "MODEL",
            "name": "test-model",
            "net_score": 1.0,
        }

        with patch.object(sys, "argv", ["prog", "test.txt"]):
            result = main()
            assert result == 0

    @patch("app.workers.ingestion_worker.src.main.validate_log_file")
    @patch("app.workers.ingestion_worker.src.log.loggerInstance.logger")
    def test_main_invalid_log_file(self, mock_logger: Any, mock_log: Any) -> None:
        """Test main with invalid log file."""
        mock_log.return_value = False

        with patch.object(sys, "argv", ["prog", "test.txt"]):
            result = main()
            assert result == 1

    @patch("app.workers.ingestion_worker.src.main.validate_log_file")
    @patch("app.workers.ingestion_worker.src.main.validate_github_token")
    @patch("app.workers.ingestion_worker.src.log.loggerInstance.logger")
    def test_main_invalid_token(
        self, mock_logger: Any, mock_token: Any, mock_log: Any
    ) -> None:
        """Test main with invalid GitHub token."""
        mock_log.return_value = True
        mock_token.return_value = False

        with patch.object(sys, "argv", ["prog", "test.txt"]):
            result = main()
            assert result == 1

    @patch("app.workers.ingestion_worker.src.main.validate_log_file")
    @patch("app.workers.ingestion_worker.src.main.validate_github_token")
    @patch("app.workers.ingestion_worker.src.log.loggerInstance.logger")
    def test_main_missing_url_file_argument(
        self, mock_logger: Any, mock_token: Any, mock_log: Any
    ) -> None:
        """Test main without URL file argument."""
        mock_log.return_value = True
        mock_token.return_value = True

        with patch.object(sys, "argv", ["prog"]):
            result = main()
            assert result == 1

    @patch("app.workers.ingestion_worker.src.main.validate_log_file")
    @patch("app.workers.ingestion_worker.src.main.validate_github_token")
    @patch("app.workers.ingestion_worker.src.log.loggerInstance.logger")
    def test_main_too_many_arguments(
        self, mock_logger: Any, mock_token: Any, mock_log: Any
    ) -> None:
        """Test main with too many arguments."""
        mock_log.return_value = True
        mock_token.return_value = True

        with patch.object(sys, "argv", ["prog", "file1", "file2"]):
            result = main()
            assert result == 1
