"""
LLM-based metadata extraction using Gemini 3.1 Flash Lite.
Extracts publisher, location, translator, and page_count from
bibliography entries where regex patterns left gaps.
"""

import json
import logging
import os
import re
import time
from typing import Optional

from google import genai
from pydantic import BaseModel, Field

from lib.encoding import is_encoding_damaged, repair_value_encoding
from lib.patterns import names_a_contribution_credit

log = logging.getLogger(__name__)

# Model configuration
MODEL_ID = "gemini-3.1-flash-lite-preview"
BATCH_SIZE = 10
TEXT_TRUNCATE = 500
REQUEST_DELAY = 0.5  # seconds between API calls
MAX_RETRIES = 3

# --- Pydantic schemas for structured output ---


class EntryExtraction(BaseModel):
    """Extracted metadata for a single bibliography entry."""

    page_id: int
    publisher: Optional[str] = Field(
        None, description="Publishing house or publisher name"
    )
    location: Optional[str] = Field(None, description="City of publication")
    translator: Optional[str] = Field(None, description="Translator name(s)")
    page_count: Optional[int] = Field(None, description="Total page count as integer")


class BatchExtraction(BaseModel):
    """Batch of extracted metadata for multiple entries."""

    entries: list[EntryExtraction]


# --- Prompt templates ---

SYSTEM_PROMPT = """You extract bibliographic metadata from Stefan Zweig bibliography entries.
Each entry contains wiki markup text from an academic bibliography.
Extract ONLY what is explicitly stated in the text.
Return null for any field where the information is not present.
Do NOT guess or infer — only extract what you can read directly."""

USER_PROMPT_TEMPLATE = """Extract the requested fields from these bibliography entries.
Only extract fields listed in "needed" — return null for all others.

{entries_json}"""


def create_client():
    """Create Gemini client. API key from GEMINI_API_KEY env var."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Add it to .env in the project root."
        )
    return genai.Client(api_key=api_key)


def prepare_batch_entry(row, needed_fields):
    """Prepare a single entry for the LLM batch request."""
    text = row.get("raw_content", "") or row.get("content", "")
    return {
        "page_id": int(row["page_id"]),
        "needed": needed_fields,
        "text": text[:TEXT_TRUNCATE],
    }


def determine_needed_fields(row):
    """Determine which fields are missing for this entry."""
    needed = []
    if not row.get("publisher"):
        needed.append("publisher")
    if not row.get("location"):
        needed.append("location")
    if not row.get("translator"):
        # Only look for translator on non-German entries
        lang = row.get("language", "")
        if lang and lang != "German":
            needed.append("translator")
        elif not lang:
            # Unknown language — might be a translation
            needed.append("translator")
    if not row.get("page_count"):
        needed.append("page_count")
    return needed


def call_gemini(client, batch_entries):
    """Send a batch of entries to Gemini and return parsed results.
    Retries on failure with exponential backoff.
    """
    entries_json = json.dumps(batch_entries, ensure_ascii=False)
    user_prompt = USER_PROMPT_TEMPLATE.format(entries_json=entries_json)

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    {
                        "role": "user",
                        "parts": [{"text": SYSTEM_PROMPT + "\n\n" + user_prompt}],
                    },
                ],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": BatchExtraction,
                },
            )
            result = BatchExtraction.model_validate_json(response.text)
            return result.entries
        except Exception as e:
            wait = (2**attempt) * 1.0
            log.warning(f"API call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(wait)
            else:
                log.error(f"Batch failed after {MAX_RETRIES} attempts, skipping")
                return []


# Mojibake patterns that indicate the LLM worsened encoding. Kept as the
# historical guard; is_encoding_damaged recognises the same signatures and the
# ones beginning with Ä or Å that this expression misses, so the two are used
# together and nothing rejected before is admitted now.
_LLM_MOJIBAKE_RE = re.compile(
    r'â€[™œ"˜]|â€™|â€œ|â€\x9d|â€\x98|Ã[\x80-\xbf]|Â[\xa0-\xff]'
)


def _has_llm_mojibake(text):
    """Detect mojibake patterns introduced by the LLM."""
    return bool(text and _LLM_MOJIBAKE_RE.search(text))


def repair_or_reject(value):
    """Repair a misread value; return None where the damage cannot be undone.

    A value the byte round-trip restores is kept in its repaired form, because
    a correct name serves the record better than an empty field. A value whose
    bytes were already lost when the cache was written is refused, because an
    empty field is a smaller claim than a corrupt one.
    """
    if not value:
        return None
    if not (is_encoding_damaged(value) or _has_llm_mojibake(value)):
        return value
    repaired = repair_value_encoding(value)
    if is_encoding_damaged(repaired) or _has_llm_mojibake(repaired):
        return None
    return repaired


def validate_extraction(extraction):
    """Validate a single LLM extraction result. Returns cleaned dict."""
    result = {"page_id": extraction.page_id}

    # Publisher: 3-80 chars, no wiki markup, repaired encoding, no credit phrase
    pub = repair_or_reject(extraction.publisher)
    if pub:
        pub = pub.strip().rstrip(".,;:")
        if (
            3 <= len(pub) <= 80
            and "[[" not in pub
            and "'''" not in pub
            and not names_a_contribution_credit(pub)
        ):
            result["publisher"] = pub

    # Location: 2-60 chars, no wiki markup, repaired encoding
    loc = repair_or_reject(extraction.location)
    if loc:
        loc = loc.strip().rstrip(".,;:")
        if 2 <= len(loc) <= 60 and "[[" not in loc and "'''" not in loc:
            result["location"] = loc

    # Translator: 3-60 chars, starts with uppercase, repaired encoding
    tr = repair_or_reject(extraction.translator)
    if tr:
        tr = tr.strip().rstrip(".,;:")
        if 3 <= len(tr) <= 60 and tr[0].isupper() and "[[" not in tr:
            result["translator"] = tr

    # Page count: 1-10000
    if extraction.page_count is not None:
        if 1 <= extraction.page_count <= 10000:
            result["page_count"] = extraction.page_count

    return result


# --- Cache management ---


def load_cache(cache_path):
    """Load existing LLM results cache."""
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache_path, cache):
    """Save LLM results cache atomically — a crash during the periodic save
    must not destroy the cache that resume depends on."""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    tmp_path = cache_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, cache_path)
