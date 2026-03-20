from __future__ import annotations

import re

from qms_doc_parser.models.parser_models import BlockReviewFeatures, BlockType, ParserBlock


_TABLE_MARKER_RE = re.compile(r"^\s*таблица\b", flags=re.IGNORECASE)
_FIGURE_MARKER_RE = re.compile(r"^\s*рисунок\b", flags=re.IGNORECASE)
_APPENDIX_MARKER_RE = re.compile(r"^\s*(приложение\s+[А-ЯA-Z]\b|[А-ЯA-Z](?:\.\d+){1,5}\b)")
_NOTE_ANCHOR_RE = re.compile(r"^\s*(примечание|note)\b", flags=re.IGNORECASE)


def annotate_blocks_for_review(blocks: list[ParserBlock]) -> None:
    for index, block in enumerate(blocks):
        previous_block = blocks[index - 1] if index > 0 else None
        next_block = blocks[index + 1] if index + 1 < len(blocks) else None

        block.prev_block_id = previous_block.block_id if previous_block else None
        block.next_block_id = next_block.block_id if next_block else None
        block.review_features = _build_review_features(blocks, index)


def _build_review_features(blocks: list[ParserBlock], index: int) -> BlockReviewFeatures:
    block = blocks[index]
    normalized_text = (block.normalized_text or "").strip()

    return BlockReviewFeatures(
        compact_section_path=_compact_section_path(block),
        heading_detection_source=_resolve_heading_detection_source(block),
        text_ends_with_colon=normalized_text.endswith(":"),
        text_starts_with_table_marker=bool(_TABLE_MARKER_RE.match(normalized_text)),
        text_starts_with_figure_marker=bool(_FIGURE_MARKER_RE.match(normalized_text)),
        looks_like_appendix_marker=bool(_APPENDIX_MARKER_RE.match(normalized_text)),
        looks_like_note_anchor=bool(_NOTE_ANCHOR_RE.match(normalized_text)),
        is_empty_or_layout_artifact=_is_empty_or_layout_artifact(block),
        next_blocks_are_list_items=_next_non_empty_block_is_list_item(blocks, index),
    )


def _compact_section_path(block: ParserBlock) -> str | None:
    if not block.section_context.section_path:
        return None
    return " > ".join(block.section_context.section_path)


def _resolve_heading_detection_source(block: ParserBlock) -> str | None:
    if not block.heading_info or not block.heading_info.detection_method:
        return None

    detection_method = block.heading_info.detection_method
    if detection_method == "style_registry":
        return "registry"
    if "fallback" in detection_method:
        return "fallback"
    return "heuristic"


def _is_empty_or_layout_artifact(block: ParserBlock) -> bool:
    if block.block_type == BlockType.empty:
        return True
    if block.flags.is_empty:
        return True
    normalized_text = (block.normalized_text or "").strip()
    return not normalized_text and block.table_info is None


def _next_non_empty_block_is_list_item(blocks: list[ParserBlock], index: int) -> bool:
    for next_block in blocks[index + 1 :]:
        if _is_empty_or_layout_artifact(next_block):
            continue
        return next_block.block_type == BlockType.list_item
    return False
