"""
LLM-as-a-Judge tests using Gemini 3.1 Flash Lite.
Sends extracted fields + raw text to Gemini for quality judgment.

Run with: pytest tests/test_llm_judge.py -m llm -v
Requires GEMINI_API_KEY in .env
"""

import json
import warnings
from typing import Literal

import pytest

# CI runs without the LLM stack installed; skip collection instead of erroring.
pytest.importorskip("pydantic", reason="pydantic not installed — LLM stack absent")
pytest.importorskip(
    "google.genai", reason="google-genai not installed — LLM stack absent"
)

from lib.llm_extract import MODEL_ID
from lib.patterns import (
    extract_language_from_category,
    extract_location,
    extract_page_count,
    extract_publisher,
    extract_translator,
    extract_year,
)
from lib.wiki_parser import extract_categories, extract_structured_data
from pydantic import BaseModel

pytestmark = pytest.mark.llm


# --- Pydantic schemas for structured judge response ---


class FieldJudgment(BaseModel):
    field: str
    verdict: Literal["correct", "wrong", "missed", "not_applicable"]
    explanation: str = ""


class JudgmentResult(BaseModel):
    page_id: int
    judgments: list[FieldJudgment]


class BatchJudgment(BaseModel):
    results: list[JudgmentResult]


# --- Judge prompt ---

JUDGE_PROMPT = """You are a quality assurance judge for bibliographic metadata extraction
from the Klawiter Stefan Zweig bibliography.

For each entry below, you receive:
- "text": the raw wiki markup of the bibliography entry
- "extracted": the fields our pipeline extracted from this text

Evaluate EACH extracted field. For each, return one of:
- "correct": the extracted value accurately reflects what is in the text
- "wrong": the extracted value is factually incorrect (explain why)
- "missed": the field is null/empty BUT the information IS present in the text
- "not_applicable": the field is null/empty AND the information is genuinely not in the text

Fields to evaluate: title, year, publisher, location, page_count, translator, language.

Important rules:
- For "publisher": the publisher name in '''[year]: Publisher, Location''' headers counts.
- For "location": city names in '''[year]: Publisher, Location''' headers count.
- For "translator": German-language entries (Category contains "German") should NOT have a translator. Return "not_applicable" if translator is null for German entries.
- For "page_count": formats like "496p.", "142 S.", "254 Seiten", "348 pages" all count. The N/(M)p. format means N is the page count.
- Be strict about "wrong" — only use it when the extracted value contradicts the text.
- Be lenient about "missed" — only flag it when the information is clearly and unambiguously stated.
"""


# Select 10 diverse entries by index from test_sample_20.json
# Covers: non-DE publisher, location-only, German negative, Chinese, film,
#         standard header, French, short text, multi-edition, Arabic
JUDGE_ENTRY_INDICES = [0, 1, 4, 5, 6, 8, 9, 12, 14, 15]


def _extract_all_fields(entry):
    """Run the full extraction pipeline on a single entry."""
    text = entry["text"]
    data = extract_structured_data(text)
    cats, _ = extract_categories(text)

    return {
        "title": data.get("title"),
        "year": extract_year(text),
        "publisher": extract_publisher(text),
        "location": extract_location(text),
        "page_count": extract_page_count(text),
        "translator": extract_translator(text),
        "language": extract_language_from_category(cats),
    }


def _call_judge(client, entries_with_extractions):
    """Send entries to Gemini for judgment."""
    entries_json = json.dumps(entries_with_extractions, ensure_ascii=False, indent=2)
    user_prompt = f"Evaluate these extractions:\n\n{entries_json}"

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[
            {"role": "user", "parts": [{"text": JUDGE_PROMPT + "\n\n" + user_prompt}]},
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": BatchJudgment,
        },
    )
    return BatchJudgment.model_validate_json(response.text)


class TestLLMJudge:
    """Use Gemini as an independent judge of extraction quality."""

    @pytest.fixture(scope="class")
    def judge_results(self, real_entries, gemini_client):
        """Run extraction + judgment for selected entries (once per class)."""
        selected = [
            real_entries[i] for i in JUDGE_ENTRY_INDICES if i < len(real_entries)
        ]

        entries_for_judge = []
        for entry in selected:
            extracted = _extract_all_fields(entry)
            entries_for_judge.append(
                {
                    "page_id": entry["page_id"],
                    "label": entry["label"],
                    "text": entry["text"][:500],
                    "extracted": extracted,
                }
            )

        result = _call_judge(gemini_client, entries_for_judge)
        return result.results

    # Known limitations that the LLM judge will flag as "wrong":
    # - title: '''[year]: Publisher''' headers returned as title via first-line fallback
    # - publisher/translator: truncated by mojibake in fixture text
    # - page_count: start page extracted from "pp. X-Y" ranges
    _KNOWN_WRONG = {
        (4303, "title"),
        (1800, "title"),
        (4473, "title"),
        (5082, "title"),
        (4376, "title"),
        (162, "title"),
        (1800, "publisher"),
        (1800, "translator"),
        (634, "page_count"),
        (533, "page_count"),
    }

    def test_no_unexpected_wrong_extractions(self, judge_results):
        """No extracted field should be wrong UNLESS it's a known limitation."""
        unexpected = []
        for result in judge_results:
            for j in result.judgments:
                if j.verdict == "wrong":
                    if (result.page_id, j.field) not in self._KNOWN_WRONG:
                        unexpected.append(
                            f"page {result.page_id}, field '{j.field}': {j.explanation}"
                        )

        assert len(unexpected) == 0, (
            f"LLM judge found {len(unexpected)} unexpected wrong extraction(s):\n"
            + "\n".join(f"  - {w}" for w in unexpected)
        )

    def test_known_limitations_count(self, judge_results):
        """Track known wrong extractions — if this number decreases, update _KNOWN_WRONG."""
        known_found = 0
        for result in judge_results:
            for j in result.judgments:
                if (
                    j.verdict == "wrong"
                    and (result.page_id, j.field) in self._KNOWN_WRONG
                ):
                    known_found += 1

        # If fewer known issues are found, some may have been fixed — update _KNOWN_WRONG
        if known_found < len(self._KNOWN_WRONG):
            warnings.warn(
                f"Only {known_found}/{len(self._KNOWN_WRONG)} known limitations triggered. "
                f"Some may have been fixed — consider updating _KNOWN_WRONG.",
                UserWarning,
                stacklevel=1,
            )

    def test_missed_fields_as_warnings(self, judge_results):
        """Report missed extractions as warnings (not failures).
        These are known limitations of the regex pipeline."""
        missed = []
        for result in judge_results:
            for j in result.judgments:
                if j.verdict == "missed":
                    missed.append(
                        f"page {result.page_id}, field '{j.field}': {j.explanation}"
                    )

        if missed:
            warnings.warn(
                f"LLM judge found {len(missed)} missed extraction(s):\n"
                + "\n".join(f"  - {m}" for m in missed),
                UserWarning,
                stacklevel=1,
            )

    def test_majority_correct(self, judge_results):
        """At least 60% of evaluated fields should be correct or not_applicable."""
        total = 0
        ok = 0
        for result in judge_results:
            for j in result.judgments:
                total += 1
                if j.verdict in ("correct", "not_applicable"):
                    ok += 1

        ratio = ok / total if total > 0 else 0
        assert ratio >= 0.6, (
            f"Only {ok}/{total} ({ratio:.0%}) fields judged correct/not_applicable. "
            f"Expected at least 60%."
        )
