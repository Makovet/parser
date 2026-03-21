from __future__ import annotations

from pathlib import Path
import sys


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parents[1]
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


_ensure_src_on_path()

from qms_doc_parser.ui.minimal_ui import launch_minimal_ui


if __name__ == "__main__":
    launch_minimal_ui()
