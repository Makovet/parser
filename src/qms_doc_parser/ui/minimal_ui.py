from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from qms_doc_parser.exporters.review_docx import export_review_docx_from_json
from qms_doc_parser.main import parse_document

DEFAULT_REGISTRY_PATH = Path("configs/style_registry_adm_tem_011_b.yaml")


@dataclass(frozen=True)
class ActionPaths:
    input_path: Path
    output_path: Path


class PathValidationError(ValueError):
    pass


def validate_action_paths(input_path: str, output_path: str, *, input_suffix: str, output_suffix: str) -> ActionPaths:
    normalized_input = input_path.strip()
    normalized_output = output_path.strip()

    if not normalized_input:
        raise PathValidationError("Не выбран входной файл.")
    if not normalized_output:
        raise PathValidationError("Не выбран выходной файл.")

    input_candidate = Path(normalized_input)
    output_candidate = Path(normalized_output)

    if input_candidate.suffix.lower() != input_suffix:
        raise PathValidationError(f"Ожидается входной файл формата {input_suffix}.")
    if output_candidate.suffix.lower() != output_suffix:
        raise PathValidationError(f"Ожидается выходной файл формата {output_suffix}.")

    return ActionPaths(input_path=input_candidate, output_path=output_candidate)


def dispatch_docx_to_json(input_path: str, output_path: str, *, registry_path: str | Path = DEFAULT_REGISTRY_PATH) -> Path:
    paths = validate_action_paths(input_path, output_path, input_suffix=".docx", output_suffix=".json")
    parse_document(input_path=paths.input_path, output_path=paths.output_path, registry_path=registry_path)
    return paths.output_path


def dispatch_json_to_review_docx(input_path: str, output_path: str) -> Path:
    paths = validate_action_paths(input_path, output_path, input_suffix=".json", output_suffix=".docx")
    export_review_docx_from_json(input_path=paths.input_path, output_path=paths.output_path)
    return paths.output_path


class MinimalUIApp:
    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.root.title("QMS DOC Parser — Minimal UI")

        self.docx_input_var = tk.StringVar(master=root)
        self.docx_output_var = tk.StringVar(master=root)
        self.json_input_var = tk.StringVar(master=root)
        self.review_output_var = tk.StringVar(master=root)
        self.status_var = tk.StringVar(master=root, value="Выберите сценарий и файлы.")

        container = ttk.Frame(root, padding=12)
        container.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        self._build_docx_to_json_section(container, row=0)
        self._build_json_to_docx_section(container, row=1)

        status_label = ttk.Label(container, textvariable=self.status_var, anchor="w")
        status_label.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(12, 0))

    def _build_docx_to_json_section(self, parent: ttk.Frame, *, row: int) -> None:
        section = ttk.LabelFrame(parent, text="DOCX -> JSON", padding=10)
        section.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        section.columnconfigure(1, weight=1)

        ttk.Label(section, text="Входной DOCX").grid(row=0, column=0, sticky="w")
        ttk.Entry(section, textvariable=self.docx_input_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(section, text="Выбрать...", command=self.choose_docx_input).grid(row=0, column=2)

        ttk.Label(section, text="Выходной JSON").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(section, textvariable=self.docx_output_var).grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(section, text="Сохранить как...", command=self.choose_docx_output).grid(row=1, column=2, pady=(6, 0))

        ttk.Button(section, text="Запустить DOCX -> JSON", command=self.run_docx_to_json).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    def _build_json_to_docx_section(self, parent: ttk.Frame, *, row: int) -> None:
        section = ttk.LabelFrame(parent, text="JSON -> review DOCX", padding=10)
        section.grid(row=row, column=0, columnspan=3, sticky="ew")
        section.columnconfigure(1, weight=1)

        ttk.Label(section, text="Входной JSON").grid(row=0, column=0, sticky="w")
        ttk.Entry(section, textvariable=self.json_input_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(section, text="Выбрать...", command=self.choose_json_input).grid(row=0, column=2)

        ttk.Label(section, text="Выходной review DOCX").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(section, textvariable=self.review_output_var).grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(section, text="Сохранить как...", command=self.choose_review_output).grid(row=1, column=2, pady=(6, 0))

        ttk.Button(section, text="Запустить JSON -> review DOCX", command=self.run_json_to_review_docx).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    def choose_docx_input(self) -> None:
        selected = filedialog.askopenfilename(title="Выберите входной DOCX", filetypes=[("DOCX files", "*.docx")])
        if selected:
            self.docx_input_var.set(selected)
            if not self.docx_output_var.get().strip():
                self.docx_output_var.set(str(Path(selected).with_suffix(".json")))

    def choose_docx_output(self) -> None:
        initial_name = Path(self.docx_input_var.get()).with_suffix(".json").name if self.docx_input_var.get().strip() else "output.json"
        selected = filedialog.asksaveasfilename(
            title="Сохранить JSON как",
            defaultextension=".json",
            initialfile=initial_name,
            filetypes=[("JSON files", "*.json")],
        )
        if selected:
            self.docx_output_var.set(selected)

    def choose_json_input(self) -> None:
        selected = filedialog.askopenfilename(title="Выберите входной JSON", filetypes=[("JSON files", "*.json")])
        if selected:
            self.json_input_var.set(selected)
            if not self.review_output_var.get().strip():
                self.review_output_var.set(str(Path(selected).with_suffix(".review.docx")))

    def choose_review_output(self) -> None:
        initial_name = Path(self.json_input_var.get()).with_suffix(".review.docx").name if self.json_input_var.get().strip() else "review.docx"
        selected = filedialog.asksaveasfilename(
            title="Сохранить review DOCX как",
            defaultextension=".docx",
            initialfile=initial_name,
            filetypes=[("DOCX files", "*.docx")],
        )
        if selected:
            self.review_output_var.set(selected)

    def run_docx_to_json(self) -> None:
        self._run_action(
            action=lambda: dispatch_docx_to_json(self.docx_input_var.get(), self.docx_output_var.get()),
            success_title="QMS DOC Parser",
            success_message="Разбор завершён успешно.",
        )

    def run_json_to_review_docx(self) -> None:
        self._run_action(
            action=lambda: dispatch_json_to_review_docx(self.json_input_var.get(), self.review_output_var.get()),
            success_title="QMS DOC Parser",
            success_message="Review DOCX экспорт завершён успешно.",
        )

    def _run_action(self, *, action, success_title: str, success_message: str) -> None:
        try:
            output_path = action()
        except PathValidationError as exc:
            self.status_var.set(str(exc))
            messagebox.showerror("QMS DOC Parser", str(exc))
        except Exception as exc:
            self.status_var.set(f"Ошибка: {exc}")
            messagebox.showerror("QMS DOC Parser", f"Операция завершилась с ошибкой:\n{exc}")
            raise
        else:
            message = f"{success_message}\n\nРезультат:\n{output_path}"
            self.status_var.set(message)
            messagebox.showinfo(success_title, message)


def launch_minimal_ui() -> None:
    root = tk.Tk()
    MinimalUIApp(root)
    root.mainloop()
