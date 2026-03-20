from __future__ import annotations


import sys
import tkinter as tk
from tkinter import filedialog, messagebox

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
