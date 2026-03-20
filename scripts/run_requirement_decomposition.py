from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


_ensure_src_on_path()

from qms_doc_parser.pipeline.parser_pipeline import parse_docx_to_document
from qms_doc_parser.requirements.decompose import build_requirement_records
from qms_doc_parser.requirements.extract import extract_requirement_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Build normalized requirement records from parsed DOCX main_body blocks")
    parser.add_argument("input_docx", help="Path to input .docx")
    parser.add_argument(
        "--registry",
        default="configs/style_registry_adm_tem_011_b.yaml",
        help="Path to style registry yaml",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to output JSON. Defaults to data/output/<input_name>.requirement_records.json",
    )

    args = parser.parse_args()
    input_path = Path(args.input_docx)
    output_path = (
        Path(args.output)
        if args.output
        else Path("data/output") / f"{input_path.stem}.requirement_records.json"
    )

    parsed = parse_docx_to_document(input_path=input_path, registry_path=args.registry)
    candidates = extract_requirement_candidates(parsed)
    records = build_requirement_records(candidates)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump([record.model_dump(mode="json") for record in records], file, ensure_ascii=False, indent=2)

    print(f"Done. Requirement records written to: {output_path}")


if __name__ == "__main__":
    main()
