"""Prompt templates for ingestion-time LLM analyses."""

# flake8: noqa: E501

from __future__ import annotations

DATASET_CODE_EXTRACTION_PROMPT = """You are a dataset and code-reference extraction system for a machine learning model registry.

Given the README text of a Hugging Face model, extract ALL datasets and ALL code repositories
mentioned in the text, and also choose ONE primary dataset for rating.

Your output MUST be a JSON object with the following exact fields:

{{
  "datasets": [...],
  "primary_dataset": null,
  "code_repos": [...],
  "notes": "..."
}}

Field semantics:

1. "datasets" (list of strings)
   - List of ALL datasets or data sources mentioned in the README that are used to
     train, fine-tune, or evaluate the model.
   - Include:
     - Named datasets (e.g., "BookCorpus", "C4", "SQuAD v1.1", "WebText").
     - Descriptive sources if that’s all that’s given (e.g., "English Wikipedia",
       "680,000 hours of multilingual speech from the web").
     - Dataset URLs if present (e.g., "https://huggingface.co/datasets/bookcorpus").
   - If a dataset is a Hugging Face dataset with a repo id like "owner/name"
     (e.g., "lerobot/pusht"), ALWAYS return ONLY that repo id string
     (e.g., "lerobot/pusht") in "datasets" and "primary_dataset",
     with NO extra titles or parentheses.
   - Do NOT invent dataset names that are not clearly implied by the README.
   - Normalize obvious names to a clean, human-readable form (e.g., "bookcorpus"
     -> "BookCorpus", "c4" -> "C4").

2. "primary_dataset" (string or null)
   - This is the ONE dataset that should be treated as the main dataset for rating.
   - Selection rules, in order of priority:
     a) If the README explicitly mentions a fine-tuning dataset (phrases like
        "fine-tuned on", "finetuned on", "fine-tuned using"), choose THAT dataset.
     b) Otherwise, choose the main pretraining dataset if clearly indicated (e.g.,
        "pretrained on BookCorpus and English Wikipedia" -> pick "BookCorpus").
     c) If multiple datasets seem equally important and no fine-tuning dataset is
        clearly highlighted, choose the FIRST dataset mentioned in the README.
     d) If no dataset or data source is mentioned at all, set "primary_dataset" to null.
   - "primary_dataset" must either be:
     - one of the entries in "datasets", or
     - null if nothing is mentioned.

3. "code_repos" (list of strings)
   - List of URLs for code repositories or official codebases used to implement,
     train, or reproduce the model.
   - Typically GitHub URLs (e.g., "https://github.com/google-research/bert",
     "https://github.com/openai/whisper"), but can include other official repo URLs.
   - Include links to Hugging Face Transformers examples or training scripts if
     they are clearly referenced as the implementation code.
   - Do NOT include random links that are not clearly code-related.

4. "notes" (string)
   - 1–3 sentences briefly explaining how you chose the datasets and primary_dataset.
   - Mention any ambiguity, assumptions, or if no datasets/code were found.

Important constraints:

- DO NOT guess datasets or code repositories that are not supported by the README text.
- If no datasets are mentioned, return "datasets": [] and "primary_dataset": null.
- If no code repositories are mentioned, return "code_repos": [].
- Your entire response MUST be valid JSON and MUST NOT contain any text outside the JSON object.

Now process the following README text and produce the JSON object:

{readme}
"""


def build_dataset_code_extraction_prompt(readme: str) -> str:
    """Inject README content into the dataset/code extraction prompt."""
    return DATASET_CODE_EXTRACTION_PROMPT.format(readme=readme)
