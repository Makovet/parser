from __future__ import annotations

from collections import defaultdict

from docx.table import Table

from qms_doc_parser.models.parser_models import CellFormattingSnapshot, TableCellRaw, TableInfo


def parse_table(table: Table, table_index: int) -> TableInfo:
    """Parse a DOCX table into a minimal structured representation.

    Notes:
    - ``row.cells`` in python-docx already exposes a rectangular grid, but merged
      cells can appear as repeated references to the same underlying XML cell.
    - We use that behavior for ``cells_normalized`` and additionally compute
      row/col spans in ``cells_raw`` by grouping coordinates with the same XML id.
    """

    grid = [[cell for cell in row.cells] for row in table.rows]
    rows_count = len(grid)
    cols_count = max((len(row) for row in grid), default=0)

    normalized_cells = _build_normalized_cells(grid, cols_count)
    cells_raw = _build_raw_cells(grid)

    return TableInfo(
        table_id=f"tbl_{table_index:04d}",
        table_index=table_index,
        rows_count=rows_count,
        cols_count=cols_count,
        header_row_count=1 if rows_count > 0 else 0,
        table_style=table.style.name if table.style is not None else None,
        has_header_row=rows_count > 0,
        cells_raw=cells_raw,
        cells_normalized=normalized_cells,
    )


def _build_normalized_cells(grid: list[list], cols_count: int) -> list[list[str | None]]:
    normalized: list[list[str | None]] = []

    for row in grid:
        normalized_row = [_normalize_cell_text(cell.text) for cell in row]
        if len(normalized_row) < cols_count:
            normalized_row.extend([None] * (cols_count - len(normalized_row)))
        normalized.append(normalized_row)

    return normalized


def _build_raw_cells(grid: list[list]) -> list[list[TableCellRaw]]:
    positions_by_tc: dict[int, list[tuple[int, int]]] = defaultdict(list)

    for row_index, row in enumerate(grid):
        for col_index, cell in enumerate(row):
            positions_by_tc[id(cell._tc)].append((row_index, col_index))

    origin_to_cell: dict[tuple[int, int], TableCellRaw] = {}
    for coordinates in positions_by_tc.values():
        top = min(r for r, _ in coordinates)
        left = min(c for _, c in coordinates)
        bottom = max(r for r, _ in coordinates)
        right = max(c for _, c in coordinates)

        origin_row = grid[top]
        origin_cell = origin_row[left]

        origin_to_cell[(top, left)] = TableCellRaw(
            text=_normalize_cell_text(origin_cell.text),
            row_index=top,
            col_index=left,
            row_span=(bottom - top) + 1,
            col_span=(right - left) + 1,
            formatting=_extract_cell_formatting(origin_cell),
        )

    cells_raw: list[list[TableCellRaw]] = []
    for row_index, row in enumerate(grid):
        raw_row: list[TableCellRaw] = []
        for col_index, _ in enumerate(row):
            raw_cell = origin_to_cell.get((row_index, col_index))
            if raw_cell is not None:
                raw_row.append(raw_cell)
        cells_raw.append(raw_row)

    return cells_raw


def _normalize_cell_text(text: str | None) -> str | None:
    if text is None:
        return None

    normalized = " ".join(text.split())
    return normalized or None


def _extract_cell_formatting(cell) -> CellFormattingSnapshot:
    first_paragraph = cell.paragraphs[0] if cell.paragraphs else None
    style_name = first_paragraph.style.name if first_paragraph is not None and first_paragraph.style is not None else None
    paragraph_alignment = first_paragraph.alignment.name.lower() if first_paragraph is not None and first_paragraph.alignment is not None else None
    vertical_alignment = cell.vertical_alignment.name.lower() if cell.vertical_alignment is not None else None
    return CellFormattingSnapshot(
        cell_source_style=style_name,
        horizontal_alignment=paragraph_alignment,
        vertical_alignment=vertical_alignment,
    )
