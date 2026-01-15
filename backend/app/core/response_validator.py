"""
Runtime response validator.

Validates:
- JSON schema shape
- provenance / sources sanity
- simple NER-to-chunk provenance check
- quote length rule (>25 words verbatim inside quotes)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


FALLBACK_RESPONSE: Dict[str, Any] = {
    "answer": "UNKNOWN IN BOOK — The provided text does not contain information to answer this question.",
    "confidence": 0.0,
    "style_score": "summary",
    "sources": [],
    "explanation": "The retrieved book excerpts do not contain enough information to answer.",
    "notes": "UNKNOWN IN BOOK",
}


@dataclass
class ValidationResult:
    ok: bool
    reason: Optional[str] = None
    notes: Optional[str] = None


class ResponseValidator:
    """
    Lightweight validator intended to be deterministic and dependency-light.

    NOTE: This is not a perfect hallucination detector. It enforces a
    conservative policy and will reject outputs that mention entities that
    do not appear in retrieved chunks.
    """

    _allowed_style_scores = {"literal", "interpretive", "summary", "concise", "detailed", "unknown"}

    def validate(
        self,
        response: Dict[str, Any],
        retrieved_chunks: List[Dict[str, Any]],
        min_confidence: float = 0.35,
    ) -> ValidationResult:
        schema_ok, schema_reason = self._validate_schema(response)
        if not schema_ok:
            return ValidationResult(False, schema_reason, "validator_rejected")

        # If generator says UNKNOWN, accept (but ensure sources empty)
        notes = (response.get("notes") or "").strip()
        if notes == "UNKNOWN IN BOOK" or str(response.get("answer", "")).startswith("UNKNOWN IN BOOK"):
            if response.get("sources"):
                return ValidationResult(False, "unknown_answer_has_sources", "validator_rejected")
            return ValidationResult(True)

        # Quote rule: any quoted span >25 words is rejected.
        quote_ok, quote_reason = self._validate_quote_length(response.get("answer", ""))
        if not quote_ok:
            return ValidationResult(False, quote_reason, "quote_too_long")

        # Low-confidence behavior is handled by orchestrator, but validator can flag it.
        try:
            conf = float(response.get("confidence", 0.0))
        except Exception:
            conf = 0.0
        if conf < min_confidence:
            return ValidationResult(False, "confidence_below_threshold", "unsure")

        # Provenance sanity: sources must be subset of retrieved chunks IDs
        retrieved_ids = {c.get("chunk_id") for c in retrieved_chunks if c.get("chunk_id")}
        sources = response.get("sources") or []
        if not isinstance(sources, list) or any(not isinstance(x, str) for x in sources):
            return ValidationResult(False, "sources_invalid", "validator_rejected")
        if any(src not in retrieved_ids for src in sources):
            return ValidationResult(False, "sources_not_subset_of_retrieved", "validator_rejected")

        # NER/provenance check: every extracted entity must appear in at least one chunk text.
        chunks_text = "\n".join([str(c.get("chunk_text", "")) for c in retrieved_chunks])
        entity_ok, entity_reason = self._validate_entities_present(response.get("answer", ""), chunks_text)
        if not entity_ok:
            return ValidationResult(False, entity_reason, "validator_rejected")

        return ValidationResult(True)

    def _validate_schema(self, response: Dict[str, Any]) -> Tuple[bool, str]:
        required = {"answer", "confidence", "style_score", "sources", "explanation", "notes"}
        missing = [k for k in required if k not in response]
        if missing:
            return False, f"missing_keys:{','.join(missing)}"

        if not isinstance(response.get("answer"), str):
            return False, "answer_not_string"

        try:
            conf = float(response.get("confidence"))
        except Exception:
            return False, "confidence_not_float"
        if conf < 0.0 or conf > 1.0:
            return False, "confidence_out_of_range"

        style = response.get("style_score")
        if not isinstance(style, str) or style not in self._allowed_style_scores:
            return False, "style_score_invalid"

        sources = response.get("sources")
        if not isinstance(sources, list) or any(not isinstance(x, str) for x in sources):
            return False, "sources_invalid"

        if not isinstance(response.get("explanation"), str):
            return False, "explanation_not_string"

        # notes can be None or string
        notes = response.get("notes")
        if notes is not None and not isinstance(notes, str):
            return False, "notes_not_string"

        return True, "ok"

    def _validate_quote_length(self, answer: str) -> Tuple[bool, str]:
        # Any text inside straight quotes "..." longer than 25 words is rejected.
        for m in re.finditer(r"\"([^\"]+)\"", answer):
            span = m.group(1).strip()
            if not span:
                continue
            if len(span.split()) > 25:
                return False, "quote_over_25_words"
        return True, "ok"

    def _extract_entities(self, answer: str) -> List[str]:
        """
        Simple heuristic entity extractor:
        - sequences of Capitalized words (e.g., 'New York', 'John Smith')
        - acronyms/all-caps tokens length>=2 (e.g., 'NASA')
        """
        entities: List[str] = []

        # Acronyms
        for tok in re.findall(r"\b[A-Z]{2,}\b", answer):
            entities.append(tok)

        # Proper-noun phrases: 2+ words capitalized
        for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\b", answer):
            entities.append(m.group(1))

        # De-dup preserve order
        seen = set()
        out = []
        for e in entities:
            e_norm = e.strip()
            if not e_norm:
                continue
            if e_norm.lower() in seen:
                continue
            seen.add(e_norm.lower())
            out.append(e_norm)
        return out

    def _validate_entities_present(self, answer: str, chunks_text: str) -> Tuple[bool, str]:
        hay = chunks_text.lower()
        for ent in self._extract_entities(answer):
            if ent.lower() not in hay:
                return False, f"entity_not_in_chunks:{ent}"
        return True, "ok"

