from __future__ import annotations

from pathlib import Path
from docx import Document


def load_docx(path: str | Path) -> Document:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {path}")

    if path.suffix.lower() != ".docx":
        raise ValueError(f"Expected .docx file, got: {path.suffix}")

    return Document(str(path))