"""HTTP clients for fetching artifact metadata from external services."""

import os
import time
from typing import Any, Optional
from urllib.parse import quote_plus, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()


class _Client:
    """A base client for interacting with the API metadata.

    Attributes:
        base_url (str): The base URL for the API.
    """

    def __init__(self, base_url: str):
        """Initialize the Client with a base URL.

        Args:
            base_url (str): The base URL for the API.
        """
        self.base_url = base_url.strip("/")

    def _get_json(
        self,
        path: str,
        retries: int,
        backoff: float = 2.0,
        headers: dict[str, Any] = {},
    ) -> Any:
        """Perform a GET request to the specified path and return the JSON response."""
        url = self.base_url + path

        last_response: Optional[requests.Response] = None
        last_exc: Optional[BaseException] = None

        for attempt in range(retries + 1):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                last_response = response

                # Raise for HTTP errors (4xx/5xx)
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as exc:
                last_exc = exc

                status = response.status_code  # safe: response exists here

                # Retry on 5xx
                if status >= 500 and attempt < retries:
                    wait_time = backoff * (2**attempt)
                    time.sleep(wait_time)
                    continue

                # Retry on 429 with Retry-After if provided
                if status == 429 and attempt < retries:
                    wait_header = response.headers.get(
                        "Retry-After", backoff * (2**attempt)
                    )
                    try:
                        wait_time = float(wait_header)
                    except (TypeError, ValueError):
                        wait_time = backoff * (2**attempt)
                    time.sleep(wait_time)
                    continue

                # Non-retryable HTTP error or retries exhausted
                break

            except requests.exceptions.RequestException as exc:
                # This is where response may NOT exist — so don't touch it.
                last_exc = exc
                if attempt < retries:
                    wait_time = backoff * (2**attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    break

        # --- If we reached here, all attempts failed ---

        if last_response is not None:
            # We had at least one HTTP response; use its status/text
            raise RuntimeError(
                f"HTTP {last_response.status_code} for {url}: {last_response.text}"
            ) from last_exc
        elif last_exc is not None:
            # Network-level failure, no HTTP response
            raise RuntimeError(
                f"Request to {url} failed after {retries + 1} attempts: {last_exc}"
            ) from last_exc
        else:
            # Extremely unlikely, but keeps mypy/linters happy
            raise RuntimeError(f"Request to {url} failed for unknown reasons")


class HFClient(_Client):
    """A client for interacting with the Hugging Face API.

    Attributes:
        base_url (str): The base URL for the Hugging Face API.
    """

    def __init__(self, base_url: str = "https://huggingface.co"):
        """Initialize the HFClient with a base URL.

        Args:
            base_url (str): The base URL for the Hugging Face API.
                Defaults to "https://huggingface.co".
        """
        super().__init__(base_url=base_url)

    def _headers(self) -> dict[str, Any]:
        """Return headers with optional bearer token."""
        token = os.environ.get("HUGGINGFACE_HUB_TOKEN")
        headers: dict[str, Any] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def get_model_metadata(self, repo_id: str, retries: int = 0) -> dict[str, Any]:
        """Retrieve metadata for a specific model from the Hugging Face API.

        Args:
            repo_id (str): The repository ID of the model.

        Returns:
            dict[str, Any]: The metadata of the model.

        Raises:
            ValueError: If the response data is not a dictionary.
        """
        path = f"/api/models/{repo_id}"
        data = self._get_json(path, retries, headers=self._headers())
        if not isinstance(data, dict):
            raise ValueError(
                f"Unexpected shape for model metadata at {self.base_url}{path}: "
                f"{type(data).__name__}"
            )

        data["num_contributors"] = None
        return data

    def get_dataset_metadata(self, repo_id: str, retries: int = 0) -> dict[str, Any]:
        """Retrieve metadata for a specific dataset from the Hugging Face API.

        Args:
            repo_id (str): The repository ID of the dataset.

        Returns:
            dict[str, Any]: The metadata of the dataset.

        Raises:
            ValueError: If the response data is not a dictionary.
        """
        path = f"/api/datasets/{repo_id}"
        data = self._get_json(path, retries, headers=self._headers())
        if not isinstance(data, dict):
            raise ValueError(
                f"Unexpected shape for dataset metadata at {self.base_url}{path}: "
                f"{type(data).__name__}"
            )

        data["num_contributors"] = None
        return data

    def get_space_metadata(self, repo_id: str, retries: int = 0) -> dict[str, Any]:
        """Retrieve metadata for a specific code space from the Hugging Face API.

        Args:
            repo_id (str): The repository ID of the code space.

        Returns:
            dict[str, Any]: The metadata of the code space.

        Raises:
            ValueError: If the response data is not a dictionary.
        """
        path = f"/api/spaces/{repo_id}"
        data = self._get_json(path, retries, headers=self._headers())
        if not isinstance(data, dict):
            raise ValueError(
                f"Unexpected shape for space metadata at {self.base_url}{path}: "
                f"{type(data).__name__}"
            )

        data["num_contributors"] = None
        return data


class GitHubClient(_Client):
    """A client for interacting with the GitHub API.

    Attributes:
        base_url (str): The base URL for the GitHub API.
    """

    def __init__(self, base_url: str = "https://api.github.com/repos"):
        """Initialize the GitHubClient with a base URL.

        Args:
            base_url (str): The base URL for the GitHub API.
                Defaults to "https://api.github.com/repos".
        """
        super().__init__(base_url=base_url)

    def _github_owner_repo_from_url(self, url: str) -> tuple[str, str]:
        path = urlparse(url)
        parts = [x for x in path.path.strip("/").split("/") if x]
        return parts[0], parts[1]

    def get_metadata(
        self, url: str, retries: int = 0, token: Optional[str] = None
    ) -> dict[str, Any]:
        """Retrieve metadata for a specific repository from the GitHub API.

        Args:
            url: The GitHub repository URL
            retries: Number of retry attempts for failed requests
            token: Optional GitHub API token for authentication

        Returns:
            dict[str, Any]: The metadata of the repository.

        Raises:
            ValueError: If the response data is not a dictionary.
        """
        owner, repo = self._github_owner_repo_from_url(url)
        path = f"/{owner}/{repo}"
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = self._get_json(path, retries, headers=headers)
        if not isinstance(data, dict):
            raise ValueError(
                f"Unexpected shape for GitHub metadata at {self.base_url}{path}: "
                f"{type(data).__name__}"
            )

        # Try to get contributors, but don't fail if it doesn't work
        try:
            data["num_contributors"] = self._get_number_contributors(
                owner, repo, retries=retries, token=token
            )
        except Exception:
            data["num_contributors"] = None

        return data

    def _get_number_contributors(
        self, owner: str, repo: str, retries: int = 0, token: Optional[str] = None
    ) -> Optional[int]:
        """Get the number of contributors for a GitHub repository.

        Args:
            owner: The repository owner (username or organization)
            repo: The repository name
            retries: Number of retry attempts for failed requests
            token: Optional GitHub API token for authentication

        Returns:
            Number of contributors, or None if the request fails
        """
        path = f"/{owner}/{repo}/contributors"
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = self._get_json(path, retries, headers=headers)
        if not isinstance(data, list):
            return None
        return len(data)


class GitLabClient(_Client):
    """A client for interacting with the GitLab API.

    Attributes:
        base_url (str): The base URL for the GitLab API.
    """

    def __init__(self, base_url: str = "https://gitlab.com/api/v4/projects"):
        """Initialize the GitLabClient with a base URL.

        Args:
            base_url (str): The base URL for the GitLab API.
                Defaults to "https://gitlab.com/api/v4/projects".
        """
        super().__init__(base_url=base_url)

    def _gitlab_owner_repo_from_url(self, url: str) -> str:
        path = urlparse(url)
        parts = [x for x in path.path.strip("/").split("/") if x]
        return "/".join(parts)

    def get_metadata(
        self, url: str, retries: int = 0, token: Optional[str] = None
    ) -> dict[str, Any]:
        """Retrieve metadata for a specific repository from the GitLab API.

        Args:
            url: The GitLab repository URL
            retries: Number of retry attempts for failed requests
            token: Optional GitLab API token for authentication

        Returns:
            dict[str, Any]: The metadata of the repository.

        Raises:
            ValueError: If the response data is not a dictionary.
        """
        ns_name = self._gitlab_owner_repo_from_url(url)
        path = f"/{quote_plus(ns_name)}"
        headers = {"PRIVATE-TOKEN": token} if token else {}
        data = self._get_json(path, retries, headers=headers)
        if not isinstance(data, dict):
            raise ValueError(
                f"Unexpected shape for GitLab metadata at {self.base_url}{path}: "
                f"{type(data).__name__}"
            )

        # Try to get contributors, but don't fail if it doesn't work
        try:
            data["num_contributors"] = self._get_number_contributors(
                ns_name, retries, token
            )
        except Exception:
            data["num_contributors"] = None

        return data

    def _get_number_contributors(
        self, ns_name: str, retries: int = 0, token: Optional[str] = None
    ) -> Optional[int]:
        """Get the number of contributors for a GitLab repository.

        Args:
            ns_name: The namespace and project name (e.g., "group/project")
            retries: Number of retry attempts for failed requests
            token: Optional GitLab API token for authentication

        Returns:
            Number of contributors, or None if the request fails
        """
        path = f"/{quote_plus(ns_name)}/repository/contributors"  # URL-encoded id
        headers = {"PRIVATE-TOKEN": token} if token else {}

        data = self._get_json(path, retries, headers=headers)
        if not isinstance(data, list):
            return None
        return len(data)


if __name__ == "__main__":
    import json

    #     hf_client = HFClient()
    #     # resp = hf_client.get_model_metadata("google-bert/bert-base-uncased")
    #     resp = hf_client.get_dataset_metadata("bookcorpus")
    #     with open("response.json", "w") as fp:
    #         json.dump(resp, fp)

    github_client = GitHubClient()
    resp = github_client.get_metadata(
        "https://github.com/huggingface/transformers-research-projects/"
        "tree/main/distillation"
    )
    with open("response.json", "w") as fp:
        json.dump(resp, fp)
