from __future__ import annotations

from typing import Iterator, Literal, Any
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


def iter_block_items(document: DocxDocument) -> Iterator[tuple[Literal["paragraph", "table"], Any]]:
    """
    Yields paragraphs and tables in the original document order.
    """
    parent_elm = document.element.body
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield "paragraph", Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield "table", Table(child, document)