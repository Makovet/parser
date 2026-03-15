from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys


def _ensure_src_on_path() -> None:
    """Allow running CLI without editable install (src layout)."""
    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    src_path_str = str(src_path)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)


_ensure_src_on_path()


def _missing_dependencies() -> list[str]:
    required_modules = {
        "pydantic": "pydantic>=2.6.0",
        "yaml": "PyYAML>=6.0.1",
        "docx": "python-docx>=1.1.0",
    }
    missing: list[str] = []
    for module_name, package_name in required_modules.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)
    return missing


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

    missing = _missing_dependencies()
    if missing:
        missing_list = ", ".join(missing)
        raise SystemExit(
            "Missing runtime dependencies: "
            f"{missing_list}. Install them with `python -m pip install -e .` "
            "or `python -m pip install pydantic PyYAML python-docx`."
        )

    from qms_doc_parser.main import parse_document

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
