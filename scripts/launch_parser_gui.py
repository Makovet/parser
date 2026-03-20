from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox


def _ensure_src_on_path() -> Path:
    """Allow running launcher without editable install (src layout)."""
    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    src_path_str = str(src_path)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)
    return project_root


PROJECT_ROOT = _ensure_src_on_path()
DEFAULT_REGISTRY = PROJECT_ROOT / "configs" / "style_registry_adm_tem_011_b.yaml"


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


def build_default_output_path(input_path: str | Path) -> Path:
    input_path = Path(input_path)
    return PROJECT_ROOT / "data" / "output" / f"{input_path.stem}.json"


def main() -> None:
    root = tk.Tk()
    root.withdraw()

    missing = _missing_dependencies()
    if missing:
        missing_list = ", ".join(missing)
        messagebox.showerror(
            "QMS DOC Parser",
            (
                "Не хватает зависимостей: "
                f"{missing_list}.\n\n"
                "Установите их командой:\n"
                "python -m pip install -e ."
            ),
        )
        return

    input_file = filedialog.askopenfilename(
        title="Выберите DOCX-файл для разбора",
        initialdir=str(PROJECT_ROOT / "data" / "input"),
        filetypes=[("DOCX files", "*.docx")],
    )
    if not input_file:
        return

    input_path = Path(input_file)
    suggested_output = build_default_output_path(input_path)

    output_file = filedialog.asksaveasfilename(
        title="Куда сохранить JSON",
        initialdir=str(suggested_output.parent),
        initialfile=suggested_output.name,
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
    )
    if not output_file:
        return

    from qms_doc_parser.main import parse_document

    try:
        parse_document(
            input_path=input_path,
            output_path=output_file,
            registry_path=DEFAULT_REGISTRY,
        )
    except Exception as exc:
        messagebox.showerror("QMS DOC Parser", f"Не удалось разобрать документ:\n{exc}")
        return

    messagebox.showinfo(
        "QMS DOC Parser",
        (
            "Разбор завершён успешно.\n\n"
            f"Файл: {input_path.name}\n"
            f"JSON: {output_file}"
        ),
    )


if __name__ == "__main__":
    main()
