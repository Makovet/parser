from __future__ import annotations

from datetime import datetime
from pathlib import Path

from qms_doc_parser.classifiers.style_classifier import ClassificationInput, StyleClassifier
from qms_doc_parser.extractors.block_iterator import iter_block_items
from qms_doc_parser.io.docx_loader import load_docx
from qms_doc_parser.parsers.table_parser import parse_table
from qms_doc_parser.models.parser_models import (
    BlockType,
    DocumentZone,
    ParserBlock,
    ParserDocument,
    SectionContext,
    SourceLocation,
    SourceMeta,
    StructureSummary,
)
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

    current_zone: str | None = None

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
        blocks=blocks,
    )
    return parsed


def _resolve_table_zone(current_zone: str | None) -> DocumentZone:
    if current_zone and current_zone in DocumentZone._value2member_map_:
        return DocumentZone(current_zone)

    return DocumentZone.main_body


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
        total_notes=sum(1 for b in blocks if b.block_type == BlockType.note_like),
    )