from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class DocumentZone(str, Enum):
    title_page = "title_page"
    control_sheet = "control_sheet"
    toc = "toc"
    main_body = "main_body"
    appendix = "appendix"
    bibliography = "bibliography"
    template_instruction = "template_instruction"
    a3_template_section = "a3_template_section"
    footer_or_header = "footer_or_header"
    unknown_zone = "unknown_zone"


class BlockType(str, Enum):
    heading = "heading"
    appendix_heading = "appendix_heading"
    paragraph = "paragraph"
    list_item = "list_item"
    table = "table"
    table_label = "table_label"
    table_caption = "table_caption"
    table_header_cell = "table_header_cell"
    table_stub_cell = "table_stub_cell"
    table_body_cell = "table_body_cell"
    figure = "figure"
    figure_caption = "figure_caption"
    figure_explanation = "figure_explanation"
    formula = "formula"
    formula_number = "formula_number"
    formula_explanation = "formula_explanation"
    note_label = "note_label"
    note_text = "note_text"
    note_like = "note_like"
    bibliography_item = "bibliography_item"
    toc_item = "toc_item"
    title_meta = "title_meta"
    code_block = "code_block"
    code_inline = "code_inline"
    template_instruction = "template_instruction"
    empty = "empty"
    unknown = "unknown"


class ListType(str, Enum):
    numbered = "numbered"
    bulleted = "bulleted"
    lettered = "lettered"
    unknown = "unknown"


class StyleFlags(BaseModel):
    bold: bool = False
    italic: bool = False
    underline: bool = False

    model_config = ConfigDict(extra="forbid")


class IndentInfo(BaseModel):
    left: Optional[int] = None
    first_line: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class BlockFlags(BaseModel):
    is_empty: bool = False
    is_suspicious: bool = False
    needs_review: bool = False
    is_template_instruction: bool = False
    is_template_placeholder: bool = False
    is_example_content: bool = False
    is_front_matter: bool = False
    is_generated_toc_entry: bool = False
    is_header_footer_artifact: bool = False
    is_deletable_template_content: bool = False

    model_config = ConfigDict(extra="forbid")


class HeadingInfo(BaseModel):
    heading_level: Optional[int] = None
    heading_number: Optional[str] = None
    heading_title: Optional[str] = None
    detection_method: Optional[str] = None
    confidence: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class ListInfo(BaseModel):
    list_type: Optional[ListType] = None
    list_marker: Optional[str] = None
    list_level: Optional[int] = None
    list_parent_block_id: Optional[str] = None
    list_parent_marker: Optional[str] = None
    list_path: List[str] = Field(default_factory=list)
    detection_method: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class TableCellRaw(BaseModel):
    text: Optional[str] = None
    row_index: Optional[int] = None
    col_index: Optional[int] = None
    row_span: int = 1
    col_span: int = 1
    formatting: Optional[CellFormattingSnapshot] = None

    model_config = ConfigDict(extra="forbid")

class TableInfo(BaseModel):
    table_id: Optional[str] = None
    table_index: Optional[int] = None
    rows_count: Optional[int] = None
    cols_count: Optional[int] = None
    header_row_count: Optional[int] = None
    table_style: Optional[str] = None
    has_header_row: Optional[bool] = None
    cells_raw: List[List[TableCellRaw]] = Field(default_factory=list)
    cells_normalized: List[List[Optional[str]]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class FigureInfo(BaseModel):
    figure_id: Optional[str] = None
    figure_index: Optional[int] = None
    has_image: bool = False
    caption_text: Optional[str] = None
    caption_block_id: Optional[str] = None
    inline_or_anchored: Optional[str] = None
    alt_text: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class FormulaInfo(BaseModel):
    formula_id: Optional[str] = None
    formula_number: Optional[str] = None
    number_block_id: Optional[str] = None
    explanation_block_ids: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class NoteInfo(BaseModel):
    note_type: Optional[str] = None
    detection_method: Optional[str] = None
    label_block_id: Optional[str] = None
    text_block_id: Optional[str] = None
    full_text: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class SectionContext(BaseModel):
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    section_level: Optional[int] = None
    section_path: List[str] = Field(default_factory=list)
    parent_section_id: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class SourceLocation(BaseModel):
    paragraph_index: Optional[int] = None
    table_index: Optional[int] = None
    row_index: Optional[int] = None
    cell_index: Optional[int] = None
    figure_index: Optional[int] = None
    header_footer: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class BlockReviewFeatures(BaseModel):
    compact_section_path: Optional[str] = None
    heading_detection_source: Optional[str] = None
    text_ends_with_colon: bool = False
    text_starts_with_table_marker: bool = False
    text_starts_with_figure_marker: bool = False
    looks_like_appendix_marker: bool = False
    looks_like_note_anchor: bool = False
    is_empty_or_layout_artifact: bool = False
    next_blocks_are_list_items: bool = False

    model_config = ConfigDict(extra="forbid")


class ParagraphFormattingSnapshot(BaseModel):
    alignment: Optional[str] = None
    left_indent_pt: Optional[float] = None
    right_indent_pt: Optional[float] = None
    first_line_indent_pt: Optional[float] = None
    space_before_pt: Optional[float] = None
    space_after_pt: Optional[float] = None
    line_spacing: Optional[float] = None
    keep_with_next: Optional[bool] = None
    keep_together: Optional[bool] = None
    page_break_before: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class RunFormattingSnapshot(BaseModel):
    text: str
    char_style: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None
    color_rgb: Optional[str] = None
    highlight: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ListFormattingSnapshot(BaseModel):
    list_id: Optional[str] = None
    level: Optional[int] = None
    marker_type: Optional[str] = None
    marker_text: Optional[str] = None
    numbering_style: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CellFormattingSnapshot(BaseModel):
    cell_source_style: Optional[str] = None
    horizontal_alignment: Optional[str] = None
    vertical_alignment: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class StyleDefaultsSnapshot(BaseModel):
    paragraph: Optional[ParagraphFormattingSnapshot] = None
    run: Optional[RunFormattingSnapshot] = None

    model_config = ConfigDict(extra="forbid")


class StyleCatalogEntry(BaseModel):
    style_name: str
    style_type: Optional[str] = None
    base_style: Optional[str] = None
    defaults: StyleDefaultsSnapshot = Field(default_factory=StyleDefaultsSnapshot)

    model_config = ConfigDict(extra="forbid")


class ReviewRenderHints(BaseModel):
    needs_review: bool = False
    is_suspicious: bool = False
    is_unresolved: bool = False
    show_in_review_docx: bool = True

    model_config = ConfigDict(extra="forbid")


class ParserBlock(BaseModel):
    block_id: str
    block_order: int
    document_zone: DocumentZone = DocumentZone.unknown_zone
    block_type: BlockType
    block_subtype: Optional[str] = None

    raw_text: Optional[str] = None
    normalized_text: Optional[str] = None
    source_style: Optional[str] = None
    prev_block_id: Optional[str] = None
    next_block_id: Optional[str] = None

    style_flags: Optional[StyleFlags] = None
    indent: Optional[IndentInfo] = None
    paragraph_formatting: Optional[ParagraphFormattingSnapshot] = None
    runs: List[RunFormattingSnapshot] = Field(default_factory=list)
    list_formatting: Optional[ListFormattingSnapshot] = None

    heading_info: Optional[HeadingInfo] = None
    list_info: Optional[ListInfo] = None
    table_info: Optional[TableInfo] = None
    figure_info: Optional[FigureInfo] = None
    formula_info: Optional[FormulaInfo] = None
    note_info: Optional[NoteInfo] = None

    section_context: SectionContext = Field(default_factory=SectionContext)
    source_location: SourceLocation = Field(default_factory=SourceLocation)
    flags: BlockFlags = Field(default_factory=BlockFlags)
    review_features: Optional[BlockReviewFeatures] = None
    review_render_hints: ReviewRenderHints = Field(default_factory=ReviewRenderHints)

    model_config = ConfigDict(extra="allow")


class SourceMeta(BaseModel):
    file_name: str
    file_type: str = "docx"
    file_hash: Optional[str] = None
    parser_version: str
    processed_at: datetime
    language: str = "ru"

    model_config = ConfigDict(extra="forbid")


class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    document_code: Optional[str] = None
    document_type: Optional[str] = None
    revision: Optional[str] = None
    confidentiality_level: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class StructureSummary(BaseModel):
    total_blocks: int = 0
    total_sections: int = 0
    total_appendix_sections: int = 0
    total_tables: int = 0
    total_figures: int = 0
    total_formulas: int = 0
    total_notes: int = 0
    total_list_items: int = 0
    total_template_instructions: int = 0

    model_config = ConfigDict(extra="forbid")


class ParserDocument(BaseModel):
    document_id: str
    template_id: str = "ADM-TEM-011_B"
    source: SourceMeta
    document_metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    structure_summary: StructureSummary = Field(default_factory=StructureSummary)
    style_registry_used: List[str] = Field(default_factory=list)
    style_catalog: List[StyleCatalogEntry] = Field(default_factory=list)
    blocks: List[ParserBlock] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class ReviewBlockSummary(BaseModel):
    block_id: str
    block_type: str
    document_zone: str
    text_preview: Optional[str] = None
    section_path: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ReviewCandidate(BaseModel):
    candidate_id: str
    block_id: str
    current_label: Optional[str] = None
    current_block_type: str
    reason_codes: List[str] = Field(default_factory=list)
    previous_blocks: List[ReviewBlockSummary] = Field(default_factory=list)
    current_block: ReviewBlockSummary
    next_blocks: List[ReviewBlockSummary] = Field(default_factory=list)
    selected_features: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
