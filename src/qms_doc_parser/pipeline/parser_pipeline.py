from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from qms_doc_parser.classifiers.style_classifier import ClassificationInput, StyleClassifier
from qms_doc_parser.extractors.block_iterator import iter_block_items
from qms_doc_parser.io.docx_loader import load_docx
from qms_doc_parser.parsers.note_parser import apply_note_grouping
from qms_doc_parser.parsers.table_parser import parse_table
from qms_doc_parser.models.parser_models import (
    BlockType,
    DocumentZone,
    ListFormattingSnapshot,
    ParagraphFormattingSnapshot,
    ParserBlock,
    ParserDocument,
    ReviewRenderHints,
    RunFormattingSnapshot,
    SectionContext,
    SourceLocation,
    SourceMeta,
    StyleCatalogEntry,
    StyleDefaultsSnapshot,
    StructureSummary,
)
from qms_doc_parser.review.block_features import annotate_blocks_for_review
from qms_doc_parser.registry.registry_loader import load_style_registry
from qms_doc_parser.trackers.section_tracker import SectionTracker


PARSER_VERSION = "0.3.1"


def parse_docx_to_document(input_path: str | Path, registry_path: str | Path) -> ParserDocument:
    input_path = Path(input_path)
    registry = load_style_registry(registry_path)
    doc = load_docx(input_path)

    classifier = StyleClassifier(registry)
    section_tracker = SectionTracker()

    blocks: list[ParserBlock] = []
    paragraph_index = 0
    table_index = 0
    block_order = 0
    used_styles: set[str] = set()

    current_zone: str | None = DocumentZone.title_page.value

    for kind, item in iter_block_items(doc):
        block_order += 1

        if kind == "paragraph":
            paragraph_index += 1

            style_name = item.style.name if item.style is not None else None
            if style_name:
                used_styles.add(style_name)

            first_run = item.runs[0] if item.runs else None
            bold = bool(first_run.bold) if first_run else False
            italic = bool(first_run.italic) if first_run else False
            underline = bool(first_run.underline) if first_run else False

            paragraph_format = item.paragraph_format
            left_indent = int(paragraph_format.left_indent.pt * 20) if paragraph_format.left_indent else None
            first_line_indent = int(paragraph_format.first_line_indent.pt * 20) if paragraph_format.first_line_indent else None

            block = classifier.classify(
                ClassificationInput(
                    block_id=f"b{block_order:06d}",
                    block_order=block_order,
                    text=item.text,
                    style_name=style_name,
                    current_zone=current_zone,
                    paragraph_index=paragraph_index,
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    left_indent=left_indent,
                    first_line_indent=first_line_indent,
                )
            )

            # Update current zone only for meaningful non-empty blocks
            if block.document_zone != DocumentZone.unknown_zone and block.block_type != BlockType.empty:
                current_zone = block.document_zone.value

            block = section_tracker.apply(block)
            block.paragraph_formatting = _build_paragraph_formatting_snapshot(item)
            block.runs = _build_run_snapshots(item)
            block.list_formatting = _build_list_formatting_snapshot(block)
            blocks.append(block)

        elif kind == "table":
            table_index += 1

            table_info = parse_table(item, table_index)

            block = ParserBlock(
                block_id=f"b{block_order:06d}",
                block_order=block_order,
                document_zone=_resolve_table_zone(current_zone),
                block_type=BlockType.table,
                block_subtype="raw_table",
                raw_text=None,
                normalized_text=None,
                table_info=table_info,
                source_style=None,
                section_context=SectionContext(),
                source_location=SourceLocation(table_index=table_index),
            )

            block = section_tracker.apply(block)
            blocks.append(block)

    apply_note_grouping(blocks)
    annotate_blocks_for_review(blocks)
    _populate_review_render_hints(blocks)

    source = SourceMeta(
        file_name=input_path.name,
        file_type="docx",
        parser_version=PARSER_VERSION,
        processed_at=datetime.utcnow(),
        language="ru",
    )

    summary = _build_summary(blocks)

    parsed = ParserDocument(
        document_id=input_path.stem,
        template_id=registry.template_id,
        source=source,
        structure_summary=summary,
        style_registry_used=sorted(used_styles),
        style_catalog=_build_style_catalog(doc),
        blocks=blocks,
    )
    return parsed


def _resolve_table_zone(current_zone: str | None) -> DocumentZone:
    if current_zone and current_zone in DocumentZone._value2member_map_:
        return DocumentZone(current_zone)

    return DocumentZone.title_page


def _build_summary(blocks: list[ParserBlock]) -> StructureSummary:
    return StructureSummary(
        total_blocks=len(blocks),
        total_tables=sum(1 for b in blocks if b.block_type == BlockType.table),
        total_list_items=sum(1 for b in blocks if b.block_type == BlockType.list_item),
        total_template_instructions=sum(1 for b in blocks if b.block_type == BlockType.template_instruction),
        total_sections=sum(1 for b in blocks if b.block_type == BlockType.heading),
        total_appendix_sections=sum(1 for b in blocks if b.block_type == BlockType.appendix_heading),
        total_figures=sum(1 for b in blocks if b.block_type == BlockType.figure),
        total_formulas=sum(1 for b in blocks if b.block_type == BlockType.formula),
        total_notes=_count_logical_notes(blocks),
    )


def _build_paragraph_formatting_snapshot(paragraph) -> ParagraphFormattingSnapshot:
    paragraph_format = paragraph.paragraph_format
    alignment = paragraph.alignment.name.lower() if paragraph.alignment is not None else None
    line_spacing = float(paragraph_format.line_spacing) if isinstance(paragraph_format.line_spacing, (int, float)) else None
    return ParagraphFormattingSnapshot(
        alignment=alignment,
        left_indent_pt=_pt_value(paragraph_format.left_indent),
        right_indent_pt=_pt_value(paragraph_format.right_indent),
        first_line_indent_pt=_pt_value(paragraph_format.first_line_indent),
        space_before_pt=_pt_value(paragraph_format.space_before),
        space_after_pt=_pt_value(paragraph_format.space_after),
        line_spacing=line_spacing,
        keep_with_next=paragraph_format.keep_with_next,
        keep_together=paragraph_format.keep_together,
        page_break_before=paragraph_format.page_break_before,
    )


def _build_run_snapshots(paragraph) -> list[RunFormattingSnapshot]:
    snapshots: list[RunFormattingSnapshot] = []
    for run in paragraph.runs:
        color_rgb = None
        if run.font.color is not None and run.font.color.rgb is not None:
            color_rgb = str(run.font.color.rgb)
        highlight = run.font.highlight_color.name.lower() if run.font.highlight_color is not None else None
        snapshots.append(
            RunFormattingSnapshot(
                text=run.text,
                char_style=run.style.name if run.style is not None else None,
                bold=run.bold,
                italic=run.italic,
                underline=run.underline,
                font_name=run.font.name,
                font_size_pt=run.font.size.pt if run.font.size is not None else None,
                color_rgb=color_rgb,
                highlight=highlight,
            )
        )
    return snapshots


def _build_list_formatting_snapshot(block: ParserBlock) -> ListFormattingSnapshot | None:
    if block.block_type != BlockType.list_item or block.list_info is None:
        return None

    marker_text = (
        block.list_info.list_marker
        or _extract_visible_list_marker(block.raw_text or block.normalized_text or "")
        or _default_marker_text(block.list_info.list_type.value if block.list_info.list_type is not None else None)
    )
    marker_type = block.list_info.list_type.value if block.list_info.list_type is not None else None
    numbering_style = "bullet" if marker_type == "bulleted" else "numbered" if marker_type == "numbered" else marker_type
    return ListFormattingSnapshot(
        list_id=block.list_info.list_parent_block_id or block.block_id,
        level=block.list_info.list_level,
        marker_type=marker_type,
        marker_text=marker_text,
        numbering_style=numbering_style,
    )


def _extract_visible_list_marker(text: str) -> str | None:
    match = re.match(r"^\s*([-•–]|\d+[\.)]|[A-Za-zА-Яа-я]\))", text)
    return match.group(1) if match else None


def _default_marker_text(marker_type: str | None) -> str | None:
    if marker_type == "bulleted":
        return "-"
    if marker_type == "numbered":
        return "1."
    if marker_type == "lettered":
        return "a)"
    return None


def _populate_review_render_hints(blocks: list[ParserBlock]) -> None:
    for block in blocks:
        metadata = getattr(block, "metadata", None)
        is_unresolved = False
        if isinstance(metadata, dict):
            is_unresolved = bool(metadata.get("is_orphan"))
        block.review_render_hints = ReviewRenderHints(
            needs_review=block.flags.needs_review,
            is_suspicious=block.flags.is_suspicious,
            is_unresolved=is_unresolved or block.flags.needs_review,
            show_in_review_docx=block.block_type != BlockType.empty,
        )


def _build_style_catalog(doc) -> list[StyleCatalogEntry]:
    entries: list[StyleCatalogEntry] = []
    for style in doc.styles:
        paragraph_defaults = _build_style_paragraph_defaults(style)
        run_defaults = _build_style_run_defaults(style)
        base_style = None
        style_base = getattr(style, "base_style", None)
        if style_base is not None:
            base_style = getattr(style_base, "name", None)
        entries.append(
            StyleCatalogEntry(
                style_name=style.name,
                style_type=getattr(style.type, "name", None).lower() if getattr(style, "type", None) is not None else None,
                base_style=base_style,
                defaults=StyleDefaultsSnapshot(
                    paragraph=paragraph_defaults,
                    run=run_defaults,
                ),
            )
        )
    return entries


def _build_style_paragraph_defaults(style) -> ParagraphFormattingSnapshot | None:
    if not hasattr(style, "paragraph_format"):
        return None
    paragraph_format = style.paragraph_format
    alignment = style.paragraph_format.alignment.name.lower() if style.paragraph_format.alignment is not None else None
    line_spacing = float(paragraph_format.line_spacing) if isinstance(paragraph_format.line_spacing, (int, float)) else None
    if all(
        value is None
        for value in (
            alignment,
            _pt_value(paragraph_format.left_indent),
            _pt_value(paragraph_format.right_indent),
            _pt_value(paragraph_format.first_line_indent),
            _pt_value(paragraph_format.space_before),
            _pt_value(paragraph_format.space_after),
            line_spacing,
            paragraph_format.keep_with_next,
            paragraph_format.keep_together,
            paragraph_format.page_break_before,
        )
    ):
        return None
    return ParagraphFormattingSnapshot(
        alignment=alignment,
        left_indent_pt=_pt_value(paragraph_format.left_indent),
        right_indent_pt=_pt_value(paragraph_format.right_indent),
        first_line_indent_pt=_pt_value(paragraph_format.first_line_indent),
        space_before_pt=_pt_value(paragraph_format.space_before),
        space_after_pt=_pt_value(paragraph_format.space_after),
        line_spacing=line_spacing,
        keep_with_next=paragraph_format.keep_with_next,
        keep_together=paragraph_format.keep_together,
        page_break_before=paragraph_format.page_break_before,
    )


def _build_style_run_defaults(style) -> RunFormattingSnapshot | None:
    font = getattr(style, "font", None)
    if font is None:
        return None
    color_rgb = str(font.color.rgb) if font.color is not None and font.color.rgb is not None else None
    highlight = font.highlight_color.name.lower() if font.highlight_color is not None else None
    if all(
        value is None
        for value in (
            font.name,
            font.size.pt if font.size is not None else None,
            font.bold,
            font.italic,
            font.underline,
            color_rgb,
            highlight,
        )
    ):
        return None
    return RunFormattingSnapshot(
        text="",
        char_style=style.name,
        bold=font.bold,
        italic=font.italic,
        underline=font.underline,
        font_name=font.name,
        font_size_pt=font.size.pt if font.size is not None else None,
        color_rgb=color_rgb,
        highlight=highlight,
    )


def _pt_value(length) -> float | None:
    if length is None:
        return None
    return round(float(length.pt), 2)

def _count_logical_notes(blocks: list[ParserBlock]) -> int:
    counted_group_ids: set[str] = set()
    total = 0

    for block in blocks:
        if block.block_type in {BlockType.note_label, BlockType.note_text}:
            metadata = getattr(block, "metadata", None)
            if isinstance(metadata, dict):
                note_group_id = metadata.get("note_group_id")
                is_orphan = metadata.get("is_orphan")
            else:
                note_group_id = None
                is_orphan = None

            if isinstance(note_group_id, str) and note_group_id:
                if note_group_id not in counted_group_ids:
                    counted_group_ids.add(note_group_id)
                    total += 1
                continue

            if is_orphan is True:
                total += 1
                continue

            total += 1
            continue

        if block.block_type == BlockType.note_like:
            total += 1

    return total
