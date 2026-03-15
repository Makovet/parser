from __future__ import annotations

from qms_doc_parser.models.parser_models import BlockType, ParserBlock

_NOTE_LABEL_STYLE = "05_ИЦЖТ_Примечание_слово"
_NOTE_TEXT_STYLE = "05_ИЦЖТ_Примечание_текст после"
_NOTE_GROUP_PREFIX = "note_group_"


def apply_note_grouping(blocks: list[ParserBlock]) -> None:
    """Assign minimal two-part note metadata by adjacency inside the same zone."""
    group_index = _detect_max_group_index(blocks)
    i = 0

    while i < len(blocks):
        block = blocks[i]
        note_type = _resolve_note_type(block)

        if note_type == BlockType.note_label:
            _set_note_block_type(block, BlockType.note_label)

            if i + 1 < len(blocks):
                next_block = blocks[i + 1]
                next_note_type = _resolve_note_type(next_block)
                if next_note_type == BlockType.note_text and next_block.document_zone == block.document_zone:
                    _set_note_block_type(next_block, BlockType.note_text)

                    existing_group_id = _shared_existing_group_id(block, next_block)
                    if existing_group_id is None:
                        group_index += 1
                        note_group_id = f"{_NOTE_GROUP_PREFIX}{group_index:04d}"
                    else:
                        note_group_id = existing_group_id

                    _set_note_metadata(
                        block,
                        note_group_id=note_group_id,
                        is_orphan=False,
                        note_role="label",
                    )
                    _set_note_metadata(
                        next_block,
                        note_group_id=note_group_id,
                        is_orphan=False,
                        note_role="text",
                    )
                    i += 2
                    continue

            _set_note_metadata(block, note_group_id=None, is_orphan=True, note_role="label")
            i += 1
            continue

        if note_type == BlockType.note_text:
            _set_note_block_type(block, BlockType.note_text)
            _set_note_metadata(block, note_group_id=None, is_orphan=True, note_role="text")

        i += 1


def _resolve_note_type(block: ParserBlock) -> BlockType | None:
    if block.source_style == _NOTE_LABEL_STYLE:
        return BlockType.note_label
    if block.source_style == _NOTE_TEXT_STYLE:
        return BlockType.note_text

    if block.block_subtype == BlockType.note_label.value:
        return BlockType.note_label
    if block.block_subtype == BlockType.note_text.value:
        return BlockType.note_text

    if block.block_type == BlockType.note_label:
        return BlockType.note_label
    if block.block_type == BlockType.note_text:
        return BlockType.note_text

    return None


def _set_note_block_type(block: ParserBlock, note_type: BlockType) -> None:
    block.block_type = note_type


def _set_note_metadata(block: ParserBlock, note_group_id: str | None, is_orphan: bool, note_role: str) -> None:
    existing_metadata = getattr(block, "metadata", None)
    metadata = dict(existing_metadata) if isinstance(existing_metadata, dict) else {}
    metadata["note_group_id"] = note_group_id
    metadata["is_orphan"] = is_orphan
    metadata["note_role"] = note_role
    block.metadata = metadata


def _shared_existing_group_id(left: ParserBlock, right: ParserBlock) -> str | None:
    left_group_id = _extract_group_id(getattr(left, "metadata", None))
    right_group_id = _extract_group_id(getattr(right, "metadata", None))
    if left_group_id and left_group_id == right_group_id:
        return left_group_id
    return None


def _detect_max_group_index(blocks: list[ParserBlock]) -> int:
    max_index = 0
    for block in blocks:
        group_id = _extract_group_id(getattr(block, "metadata", None))
        if not group_id or not group_id.startswith(_NOTE_GROUP_PREFIX):
            continue

        number = group_id[len(_NOTE_GROUP_PREFIX) :]
        if number.isdigit():
            max_index = max(max_index, int(number))

    return max_index


def _extract_group_id(metadata: object) -> str | None:
    if not isinstance(metadata, dict):
        return None

    value = metadata.get("note_group_id")
    if isinstance(value, str) and value:
        return value

    return None
