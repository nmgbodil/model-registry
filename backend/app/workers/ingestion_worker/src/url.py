"""URL categorization utilities for datasets, models, and code."""

import re
from enum import Enum
from typing import Optional

from .log import loggerInstance

# Relevant regexes:
#   Dataset URL (Hugging Face datasets): https://huggingface.co/datasets/...
#   Model URL (Hugging Face models): https://huggingface.co/...
#   Code URL (GitHub): https://github.com/...


class UrlCategory(Enum):
    """Supported URL categories."""

    DATASET = 1
    MODEL = 2
    CODE = 3
    INVALID = 4


def determine_category(link: str) -> UrlCategory:
    """Determine URL category based on simple regex patterns."""
    datasetRegex = r"https:\/\/huggingface\.co\/datasets\/[\w-]+(\/[\w-]+)*"
    modelRegex = r"https:\/\/huggingface\.co\/[\w-]+(\/[\w-]+)*"
    codeRegex = r"https:\/\/github.com\/[\w-]+(\/[\w-]+)*"

    if re.match(datasetRegex, link):
        return UrlCategory.DATASET
    elif re.match(modelRegex, link):
        return UrlCategory.MODEL
    elif re.match(codeRegex, link):
        return UrlCategory.CODE
    else:
        return UrlCategory.INVALID


class Url:
    """Wrap a URL with its derived or provided category."""

    def __init__(self, link: str, category: UrlCategory = UrlCategory.INVALID):
        self.link = link
        # If given an invalid category, determine the category ourselves.
        # If it actually is invalid, print an error.
        if category == UrlCategory.INVALID:
            self.category = determine_category(link)
            if self.category == UrlCategory.INVALID:
                loggerInstance.logger.log_info(
                    f"{link} Invalid URL: Not a dataset, model or code URL"
                )
        else:
            self.category = category

    def __str__(self) -> str:
        """Human-readable URL with category."""
        return str(self.link + " Category: " + self.category.__str__())


# A Url Set consists of a code (optional), dataset(optional) and model (required) URL
class UrlSet:
    """Container for related code/dataset/model URLs."""

    def __init__(self, code: Optional[Url], dataset: Optional[Url], model: Url):
        self.code = code
        self.dataset = dataset
        self.model = model
        if (
            (model.category != UrlCategory.MODEL)
            or (dataset is not None and dataset.category != UrlCategory.DATASET)
            or (code is not None and code.category != UrlCategory.CODE)
        ):
            loggerInstance.logger.log_info(
                "Invalid URLs passed to URL set. Ensure there is a code, dataset and "
                "model URL"
            )

    def __str__(self) -> str:
        """Human-readable set of URLs."""
        return str(self.code) + "\n" + str(self.dataset) + "\n" + str(self.model)
