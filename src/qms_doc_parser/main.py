from __future__ import annotations

import json
from pathlib import Path

from qms_doc_parser.pipeline.parser_pipeline import parse_docx_to_document


def parse_document(input_path: str | Path, output_path: str | Path, registry_path: str | Path) -> None:
    parsed = parse_docx_to_document(input_path=input_path, registry_path=registry_path)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(parsed.model_dump(mode="json", exclude_none=True), f, ensure_ascii=False, indent=2)