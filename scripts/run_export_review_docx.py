from __future__ import annotations

import argparse
from pathlib import Path
import sys


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


_ensure_src_on_path()

from qms_doc_parser.exporters.review_docx import export_review_docx_from_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Build review-friendly DOCX from ParserDocument JSON")
    parser.add_argument("input_json", help="Path to ParserDocument JSON")
    parser.add_argument("output_docx", help="Path to output review DOCX")

    args = parser.parse_args()

    export_review_docx_from_json(input_path=args.input_json, output_path=args.output_docx)
    print(f"Done. Review DOCX written to: {args.output_docx}")


if __name__ == "__main__":
    main()
