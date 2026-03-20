from __future__ import annotations

import unittest
from pathlib import Path
import sys

from scripts.launch_parser_gui import DEFAULT_REGISTRY, RUN_PARSE_SCRIPT, build_default_output_path, build_run_command


class GuiLauncherTests(unittest.TestCase):
    def test_build_default_output_path_uses_output_folder_and_json_extension(self) -> None:
        output_path = build_default_output_path("/tmp/example.docx")

        self.assertEqual(output_path.name, "example.json")
        self.assertEqual(output_path.parts[-3:], ("data", "output", "example.json"))

    def test_build_run_command_targets_existing_cli_script_and_registry(self) -> None:
        command = build_run_command("C:/docs/input.docx", "C:/out/result.json")

        self.assertEqual(
            command,
            [
                sys.executable,
                str(RUN_PARSE_SCRIPT),
                "C:/docs/input.docx",
                "--registry",
                str(DEFAULT_REGISTRY),
                "--output",
                "C:/out/result.json",
            ],
        )


if __name__ == "__main__":
    unittest.main()
