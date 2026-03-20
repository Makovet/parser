from __future__ import annotations

import re

from qms_doc_parser.requirements.models import AtomicRequirement, RequirementCandidate, RequirementRecord

_LIST_PREFIX_RE = re.compile(r"^\s*(?:[-•–]|\d+[\.)]|[A-Za-zА-Яа-я]\))\s+")
_MARKER_RE = re.compile(
    r"\b(должен|должна|должны|необходимо|следует|подлежит|обязан|обязано|обязаны)\b",
    flags=re.IGNORECASE,
)
_CONDITION_RE = re.compile(r"\b(если|при|в случае)\b", flags=re.IGNORECASE)


def build_requirement_records(candidates: list[RequirementCandidate]) -> list[RequirementRecord]:
    records: list[RequirementRecord] = []
    for index, candidate in enumerate(candidates):
        normalized_text = normalize_requirement_text(candidate.candidate_text)
        strategy = _resolve_decomposition_strategy(candidates, index, normalized_text)
        atomic_requirements = _build_atomic_requirements(candidate, normalized_text, strategy, len(records) + 1)
        records.append(
            RequirementRecord(
                requirement_id=f"reqr_{len(records) + 1:04d}",
                source_candidate_id=candidate.candidate_id,
                source_block_ids=list(candidate.source_block_ids),
                primary_block_id=candidate.primary_block_id,
                document_zone=candidate.document_zone,
                section_path=list(candidate.section_path),
                compact_section_path=candidate.compact_section_path,
                original_text=candidate.candidate_text,
                normalized_text=normalized_text,
                requirement_kind=candidate.requirement_kind,
                decomposition_strategy=strategy,
                atomic_requirements=atomic_requirements,
            )
        )
    return records


def normalize_requirement_text(text: str) -> str:
    normalized = " ".join((text or "").split())
    normalized = _LIST_PREFIX_RE.sub("", normalized)
    normalized = re.sub(r"\s+([:;,.])", r"\1", normalized)
    if normalized.endswith(":") or normalized.endswith(";"):
        normalized = normalized[:-1].rstrip()
    return normalized.strip()


def _resolve_decomposition_strategy(candidates: list[RequirementCandidate], index: int, normalized_text: str) -> str:
    candidate = candidates[index]
    if candidate.extraction_reason == "normative_context_list_item":
        return "contextual_list_item"
    if normalized_text and candidate.extraction_reason.startswith("normative_marker_") and candidate.candidate_text.rstrip().endswith(":"):
        next_candidate = candidates[index + 1] if index + 1 < len(candidates) else None
        if next_candidate and next_candidate.extraction_reason == "normative_context_list_item" and next_candidate.section_path == candidate.section_path:
            return "list_header_context"
    if len(_split_normative_sentences(normalized_text)) > 1:
        return "sentence_split"
    if ";" in normalized_text and len(_split_atomic_clauses(normalized_text)) > 1:
        return "semicolon_split"
    return "single_atomic"


def _build_atomic_requirements(
    candidate: RequirementCandidate,
    normalized_text: str,
    strategy: str,
    record_index: int,
) -> list[AtomicRequirement]:
    if strategy == "list_header_context":
        return []
    if strategy == "sentence_split":
        parts = _split_normative_sentences(normalized_text)
        return [_make_atomic_requirement(part, record_index, idx + 1, "sentence", 0.82, candidate.requirement_kind) for idx, part in enumerate(parts)]
    if strategy == "semicolon_split":
        parts = _split_atomic_clauses(normalized_text)
        return [_make_atomic_requirement(part, record_index, idx + 1, "clause", 0.8, candidate.requirement_kind) for idx, part in enumerate(parts)]
    source_span_type = "list_item" if strategy == "contextual_list_item" else "full_text"
    confidence = 0.84 if strategy == "contextual_list_item" else 0.9
    return [_make_atomic_requirement(normalized_text, record_index, 1, source_span_type, confidence, candidate.requirement_kind)]


def _split_atomic_clauses(text: str) -> list[str]:
    return [part.strip() for part in re.split(r";", text) if part.strip()]


def _split_normative_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    normative_parts = [part for part in parts if _MARKER_RE.search(part)]
    return normative_parts if len(normative_parts) > 1 else []


def _make_atomic_requirement(
    atomic_text: str,
    record_index: int,
    atomic_index: int,
    source_span_type: str,
    confidence: float | str,
    requirement_kind: str | None,
) -> AtomicRequirement:
    subject_hint, action_hint, object_hint, condition_hint = _extract_hints(atomic_text)
    if requirement_kind == "contextual_obligation" and action_hint is None:
        first_words = atomic_text.split(maxsplit=1)
        action_hint = first_words[0] if first_words else None
        object_hint = first_words[1] if len(first_words) > 1 else None
    return AtomicRequirement(
        atomic_id=f"reqa_{record_index:04d}_{atomic_index:02d}",
        atomic_text=atomic_text,
        subject_hint=subject_hint,
        action_hint=action_hint,
        object_hint=object_hint,
        condition_hint=condition_hint,
        source_span_type=source_span_type,
        confidence=confidence,
    )


def _extract_hints(text: str) -> tuple[str | None, str | None, str | None, str | None]:
    stripped = text.strip()
    condition_match = _CONDITION_RE.search(stripped)
    condition_hint = None
    text_without_condition = stripped
    if condition_match is not None:
        condition_hint = stripped[condition_match.start() :].strip()
        text_without_condition = stripped[: condition_match.start()].strip().rstrip(",")

    marker_match = _MARKER_RE.search(text_without_condition)
    if marker_match is None:
        return None, None, text_without_condition or None, condition_hint

    subject_hint = text_without_condition[: marker_match.start()].strip(" ,") or None
    tail = text_without_condition[marker_match.end() :].strip(" ,")
    if not tail:
        return subject_hint, None, None, condition_hint

    action_parts = tail.split(maxsplit=1)
    action_hint = action_parts[0]
    object_hint = action_parts[1] if len(action_parts) > 1 else None
    return subject_hint, action_hint, object_hint, condition_hint
