from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_cli_script_path(project_root: Path | None = None) -> Path:
    root = project_root or get_project_root()
    return root / "scripts" / "run_parse.py"


def get_registry_path(project_root: Path | None = None) -> Path:
    root = project_root or get_project_root()
    return root / "configs" / "style_registry_adm_tem_011_b.yaml"


def build_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".json")


def build_cli_command(input_path: Path, output_path: Path, registry_path: Path, project_root: Path | None = None) -> list[str]:
    root = project_root or get_project_root()
    cli_script = get_cli_script_path(root)
    return [
        sys.executable,
        str(cli_script),
        str(input_path),
        "--registry",
        str(registry_path),
        "--output",
        str(output_path),
    ]


def run_launcher() -> int:
    project_root = get_project_root()
    cli_script = get_cli_script_path(project_root)
    registry_path = get_registry_path(project_root)

    if not cli_script.is_file():
        messagebox.showerror("QMS DOC Parser", f"Не найден CLI-скрипт:\n{cli_script}")
        return 1

    if not registry_path.is_file():
        messagebox.showerror("QMS DOC Parser", f"Не найден registry YAML:\n{registry_path}")
        return 1

    root = tk.Tk()
    root.withdraw()

    input_file = filedialog.askopenfilename(
        parent=root,
        title="Выберите входной DOCX",
        filetypes=[("DOCX files", "*.docx")],
    )
    if not input_file:
        return 0

    input_path = Path(input_file)
    output_file = filedialog.asksaveasfilename(
        parent=root,
        title="Сохранить JSON как",
        defaultextension=".json",
        initialfile=build_output_path(input_path).name,
        filetypes=[("JSON files", "*.json")],
    )
    if not output_file:
        return 0

    output_path = Path(output_file)
    command = build_cli_command(input_path=input_path, output_path=output_path, registry_path=registry_path, project_root=project_root)

    result = subprocess.run(command, cwd=project_root, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        error_details = (result.stderr or result.stdout or "CLI завершился с ошибкой без вывода.").strip()
        messagebox.showerror(
            "QMS DOC Parser",
            (
                "Не удалось выполнить разбор документа.\n\n"
                f"Команда:\n{' '.join(command)}\n\n"
                f"Код возврата: {result.returncode}\n\n"
                f"Вывод:\n{error_details}"
            ),
        )
        return result.returncode

    messagebox.showinfo(
        "QMS DOC Parser",
        (
            "Разбор завершён успешно.\n\n"
            f"Файл: {input_path.name}\n"
            f"JSON: {output_path}"
        ),
    )
    return 0


def main() -> None:
    try:
        raise SystemExit(run_launcher())
    except SystemExit:
        raise
    except Exception as exc:
        try:
            messagebox.showerror("QMS DOC Parser", f"Непредвиденная ошибка launcher:\n{exc}")
        finally:
            raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
