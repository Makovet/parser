from __future__ import annotations

import re

from qms_doc_parser.models.parser_models import BlockType, DocumentZone, ParserBlock, ParserDocument
from qms_doc_parser.requirements.models import RequirementCandidate

_NORMATIVE_MARKERS: tuple[tuple[str, str], ...] = (
    (r"\bдолжен\b", "obligation"),
    (r"\bдолжна\b", "obligation"),
    (r"\bдолжны\b", "obligation"),
    (r"\bнеобходимо\b", "necessity"),
    (r"\bследует\b", "recommendation"),
    (r"\bподлежит\b", "obligation"),
    (r"\bобязан\b", "obligation"),
    (r"\bобязано\b", "obligation"),
    (r"\bобязаны\b", "obligation"),
)
_ALLOWED_BLOCK_TYPES = {BlockType.paragraph, BlockType.list_item, BlockType.note_text, BlockType.note_like}
_CONTEXT_BLOCK_TYPES = {BlockType.paragraph, BlockType.note_text, BlockType.note_like}


def extract_requirement_candidates(document: ParserDocument) -> list[RequirementCandidate]:
    candidates: list[RequirementCandidate] = []
    extracted_block_ids: set[str] = set()

    for index, block in enumerate(document.blocks):
        if not _is_main_body_requirement_source(block):
            continue

        text = (block.normalized_text or "").strip()
        if not text:
            continue

        marker_kind = _detect_requirement_kind(text)
        extraction_reason: str | None = None
        confidence: float | str | None = None
        requirement_kind: str | None = None

        if marker_kind is not None:
            extraction_reason = f"normative_marker_{block.block_type.value}"
            confidence = 0.95 if block.block_type != BlockType.list_item else 0.92
            requirement_kind = marker_kind
        elif block.block_type == BlockType.list_item and _has_normative_list_context(document.blocks, index, extracted_block_ids):
            extraction_reason = "normative_context_list_item"
            confidence = 0.78
            requirement_kind = "contextual_obligation"

        if extraction_reason is None:
            continue

        extracted_block_ids.add(block.block_id)
        candidates.append(
            RequirementCandidate(
                candidate_id=f"reqc_{len(candidates) + 1:04d}",
                source_block_ids=[block.block_id],
                primary_block_id=block.block_id,
                section_path=list(block.section_context.section_path),
                document_zone=block.document_zone.value,
                candidate_text=text,
                extraction_reason=extraction_reason,
                confidence=confidence,
                requirement_kind=requirement_kind,
                compact_section_path=_compact_section_path(block),
            )
        )

    return candidates


def _is_main_body_requirement_source(block: ParserBlock) -> bool:
    return block.document_zone == DocumentZone.main_body and block.block_type in _ALLOWED_BLOCK_TYPES


def _detect_requirement_kind(text: str) -> str | None:
    lowered = text.casefold()
    for pattern, kind in _NORMATIVE_MARKERS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return kind
    return None


def _has_normative_list_context(blocks: list[ParserBlock], index: int, extracted_block_ids: set[str]) -> bool:
    block = blocks[index]
    for previous in reversed(blocks[:index]):
        if previous.document_zone != DocumentZone.main_body:
            continue
        if previous.block_type == BlockType.heading:
            return False
        if previous.block_type not in _ALLOWED_BLOCK_TYPES:
            continue
        previous_text = (previous.normalized_text or "").strip()
        if not previous_text:
            continue
        if previous.block_type == BlockType.list_item:
            return previous.block_id in extracted_block_ids and previous.section_context.section_path == block.section_context.section_path
        if previous.block_type in _CONTEXT_BLOCK_TYPES:
            return _detect_requirement_kind(previous_text) is not None and previous.section_context.section_path == block.section_context.section_path
        return False
    return False


def _compact_section_path(block: ParserBlock) -> str | None:
    if not block.section_context.section_path:
        return None
    return " > ".join(block.section_context.section_path)
