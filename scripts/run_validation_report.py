from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    src_path_str = str(src_path)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)


_ensure_src_on_path()

from qms_doc_parser.validation.report import validate_docx_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Build machine-readable validation report for parser output")
    parser.add_argument("input_docx", help="Path to input .docx")
    parser.add_argument(
        "--registry",
        default="configs/style_registry_adm_tem_011_b.yaml",
        help="Path to style registry yaml",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to output JSON. Defaults to data/output/<input_name>.validation_report.json",
    )

    args = parser.parse_args()
    input_path = Path(args.input_docx)
    output_path = (
        Path(args.output)
        if args.output
        else Path("data/output") / f"{input_path.stem}.validation_report.json"
    )

    report = validate_docx_file(input_path=input_path, registry_path=args.registry)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report.model_dump(mode="json"), file, ensure_ascii=False, indent=2)

    print(f"Done. Validation report written to: {output_path}")
    if not report.downstream_ready:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
