from __future__ import annotations

import sys
import unittest
from pathlib import Path

from scripts.launch_parser_gui import build_cli_command, build_output_path


class GuiLauncherTests(unittest.TestCase):
    def test_build_output_path_replaces_docx_suffix_with_json(self) -> None:
        input_path = Path("data/input/1.docx")

        output_path = build_output_path(input_path)

        self.assertEqual(output_path, Path("data/input/1.json"))

    def test_build_cli_command_uses_existing_cli_entrypoint(self) -> None:
        project_root = Path("/workspace/parser")
        input_path = Path("data/input/1.docx")
        output_path = Path("data/output/1.json")
        registry_path = Path("configs/style_registry_adm_tem_011_b.yaml")

        command = build_cli_command(
            input_path=input_path,
            output_path=output_path,
            registry_path=registry_path,
            project_root=project_root,
        )

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], str(project_root / "scripts" / "run_parse.py"))
        self.assertEqual(
            command[2:],
            [
                str(input_path),
                "--registry",
                str(registry_path),
                "--output",
                str(output_path),
            ],
        )


if __name__ == "__main__":
    unittest.main()
