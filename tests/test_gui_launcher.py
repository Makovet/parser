from __future__ import annotations

import unittest
from pathlib import Path

from scripts.launch_parser_gui import build_default_output_path


class GuiLauncherTests(unittest.TestCase):
    def test_build_default_output_path_uses_output_folder_and_json_extension(self) -> None:
        output_path = build_default_output_path("/tmp/example.docx")

        self.assertEqual(output_path, Path("/workspace/parser/data/output/example.json"))


if __name__ == "__main__":
    unittest.main()
