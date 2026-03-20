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
from qms_doc_parser.review.review_candidates import build_review_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Build compact review candidates for a parsed DOCX")
    parser.add_argument("input_docx", help="Path to input .docx")
    parser.add_argument(
        "--registry",
        default="configs/style_registry_adm_tem_011_b.yaml",
        help="Path to style registry yaml",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to output JSON. Defaults to data/output/<input_name>.review_candidates.json",
    )

    args = parser.parse_args()

    input_path = Path(args.input_docx)
    output_path = (
        Path(args.output)
        if args.output
        else Path("data/output") / f"{input_path.stem}.review_candidates.json"
    )

    parsed = parse_docx_to_document(input_path=input_path, registry_path=args.registry)
    candidates = build_review_candidates(parsed.blocks)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump([candidate.model_dump(mode="json") for candidate in candidates], file, ensure_ascii=False, indent=2)

    print(f"Done. Review candidates written to: {output_path}")


if __name__ == "__main__":
    main()
