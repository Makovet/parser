from __future__ import annotations

from typing import Iterable

from qms_doc_parser.models.parser_models import BlockType, ParserBlock, ReviewBlockSummary, ReviewCandidate


def build_review_candidates(blocks: list[ParserBlock]) -> list[ReviewCandidate]:
    candidates: list[ReviewCandidate] = []

    for index, block in enumerate(blocks):
        reason_codes = _collect_reason_codes(blocks, index)
        if not reason_codes:
            continue

        candidates.append(
            ReviewCandidate(
                candidate_id=f"rc_{len(candidates) + 1:04d}",
                block_id=block.block_id,
                current_label=block.block_subtype or block.block_type.value,
                current_block_type=block.block_type.value,
                reason_codes=reason_codes,
                previous_blocks=_summaries(blocks[max(0, index - 2) : index]),
                current_block=_summarize_block(block),
                next_blocks=_summaries(blocks[index + 1 : index + 3]),
                selected_features=_selected_features(block),
            )
        )

    return candidates


def _collect_reason_codes(blocks: list[ParserBlock], index: int) -> list[str]:
    block = blocks[index]
    features = block.review_features
    reason_codes: list[str] = []

    if block.block_type in {BlockType.heading, BlockType.appendix_heading}:
        if block.flags.is_suspicious or block.flags.needs_review:
            reason_codes.append("suspicious_heading")
        if features and features.heading_detection_source == "fallback":
            reason_codes.append("fallback_heading")
        if features and features.text_ends_with_colon and features.next_blocks_are_list_items:
            reason_codes.append("heading_with_colon_before_list")

    if block.block_type == BlockType.figure and features and features.text_starts_with_table_marker:
        reason_codes.append("figure_text_looks_like_table")

    if block.block_type in {BlockType.note_label, BlockType.note_text, BlockType.note_like}:
        metadata = getattr(block, "metadata", None)
        is_orphan = metadata.get("is_orphan") if isinstance(metadata, dict) else None
        if is_orphan is True:
            reason_codes.append("orphan_note")
        elif features and features.looks_like_note_anchor and block.block_type == BlockType.note_like:
            reason_codes.append("note_anchor_ambiguity")

    if features and features.looks_like_appendix_marker and block.block_type != BlockType.appendix_heading:
        reason_codes.append("appendix_like_non_appendix_block")

    if _is_layout_artifact_between_related_blocks(blocks, index):
        reason_codes.append("layout_artifact_between_related_blocks")

    return reason_codes


def _is_layout_artifact_between_related_blocks(blocks: list[ParserBlock], index: int) -> bool:
    block = blocks[index]
    features = block.review_features
    if not features or not features.is_empty_or_layout_artifact:
        return False

    previous_block = blocks[index - 1] if index > 0 else None
    next_block = blocks[index + 1] if index + 1 < len(blocks) else None
    if previous_block is None or next_block is None:
        return False

    related_pairs = {
        (BlockType.table_caption, BlockType.table),
        (BlockType.note_label, BlockType.note_text),
        (BlockType.figure_caption, BlockType.figure),
    }
    return (previous_block.block_type, next_block.block_type) in related_pairs


def _selected_features(block: ParserBlock) -> dict[str, object]:
    features = block.review_features
    if features is None:
        return {}

    return {
        "compact_section_path": features.compact_section_path,
        "heading_detection_source": features.heading_detection_source,
        "text_ends_with_colon": features.text_ends_with_colon,
        "text_starts_with_table_marker": features.text_starts_with_table_marker,
        "text_starts_with_figure_marker": features.text_starts_with_figure_marker,
        "looks_like_appendix_marker": features.looks_like_appendix_marker,
        "looks_like_note_anchor": features.looks_like_note_anchor,
        "is_empty_or_layout_artifact": features.is_empty_or_layout_artifact,
        "next_blocks_are_list_items": features.next_blocks_are_list_items,
    }


def _summaries(blocks: Iterable[ParserBlock]) -> list[ReviewBlockSummary]:
    return [_summarize_block(block) for block in blocks]


def _summarize_block(block: ParserBlock) -> ReviewBlockSummary:
    return ReviewBlockSummary(
        block_id=block.block_id,
        block_type=block.block_type.value,
        document_zone=block.document_zone.value,
        text_preview=_text_preview(block),
        section_path=list(block.section_context.section_path),
    )


def _text_preview(block: ParserBlock) -> str | None:
    text = (block.normalized_text or "").strip()
    if not text:
        return None
    return text[:120]
