from __future__ import annotations

import argparse
from pathlib import Path

from qms_doc_parser.main import parse_document


def main() -> None:
    parser = argparse.ArgumentParser(description="Run QMS DOCX parser")
    parser.add_argument("input_docx", help="Path to input .docx")
    parser.add_argument(
        "--registry",
        default="configs/style_registry_adm_tem_011_b.yaml",
        help="Path to style registry yaml",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to output JSON. Defaults to data/output/<input_name>.json",
    )

    args = parser.parse_args()

    input_path = Path(args.input_docx)
    output_path = Path(args.output) if args.output else Path("data/output") / f"{input_path.stem}.json"

    parse_document(
        input_path=input_path,
        output_path=output_path,
        registry_path=args.registry,
    )

    print(f"Done. Output written to: {output_path}")


if __name__ == "__main__":
    main()