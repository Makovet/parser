from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_PARSE_SCRIPT = PROJECT_ROOT / "scripts" / "run_parse.py"
DEFAULT_REGISTRY = PROJECT_ROOT / "configs" / "style_registry_adm_tem_011_b.yaml"


def build_default_output_path(input_path: str | Path) -> Path:
    input_path = Path(input_path)
    return PROJECT_ROOT / "data" / "output" / f"{input_path.stem}.json"


def build_run_command(input_path: str | Path, output_path: str | Path) -> list[str]:
    return [
        sys.executable,
        str(RUN_PARSE_SCRIPT),
        str(Path(input_path)),
        "--registry",
        str(DEFAULT_REGISTRY),
        "--output",
        str(Path(output_path)),
    ]


def main() -> None:
    root = tk.Tk()
    root.withdraw()

    try:
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

        command = build_run_command(input_path, output_file)

        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            messagebox.showerror("QMS DOC Parser", f"Не удалось запустить парсер:\n{exc}")
            return

        if completed.returncode != 0:
            error_text = completed.stderr.strip() or completed.stdout.strip() or "Неизвестная ошибка."
            messagebox.showerror("QMS DOC Parser", f"Не удалось разобрать документ:\n{error_text}")
            return

        messagebox.showinfo(
            "QMS DOC Parser",
            (
                "Разбор завершён успешно.\n\n"
                f"Файл: {input_path.name}\n"
                f"JSON: {output_file}"
            ),
        )
    except Exception as exc:
        messagebox.showerror("QMS DOC Parser", f"Непредвиденная ошибка:\n{exc}")
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
