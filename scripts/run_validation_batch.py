from __future__ import annotations

import argparse
from pathlib import Path
import sys


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    src_path_str = str(src_path)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)


_ensure_src_on_path()

from qms_doc_parser.validation.batch import build_batch_validation_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run parser validation for multiple DOCX files and build an aggregate summary")
    parser.add_argument("inputs", nargs="*", help="DOCX files or directories containing DOCX files")
    parser.add_argument("--input-dir", default=None, help="Optional directory with DOCX files")
    parser.add_argument(
        "--registry",
        default="configs/style_registry_adm_tem_011_b.yaml",
        help="Path to style registry yaml",
    )
    parser.add_argument(
        "--reports-dir",
        default="data/output/validation_reports",
        help="Directory for per-document validation reports",
    )
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Path to aggregate batch validation JSON. Defaults to <reports-dir>/validation_batch_summary.json",
    )

    args = parser.parse_args()
    reports_dir = Path(args.reports_dir)
    summary_output = Path(args.summary_output) if args.summary_output else reports_dir / "validation_batch_summary.json"

    batch_report = build_batch_validation_report(
        args.inputs,
        input_dir=args.input_dir,
        registry_path=args.registry,
        reports_dir=reports_dir,
    )

    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(batch_report.model_dump_json(indent=2), encoding="utf-8")
    print(f"Done. Batch validation summary written to: {summary_output}")
    if batch_report.summary.failed_documents > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
