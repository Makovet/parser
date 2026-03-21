from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from qms_doc_parser.ui.minimal_ui import (
    PathValidationError,
    dispatch_docx_to_json,
    dispatch_json_to_review_docx,
    validate_action_paths,
)


class MinimalUiHelpersTests(unittest.TestCase):
    def test_validate_action_paths_accepts_expected_extensions(self) -> None:
        paths = validate_action_paths(
            "data/input/sample.docx",
            "data/output/sample.json",
            input_suffix=".docx",
            output_suffix=".json",
        )

        self.assertEqual(paths.input_path, Path("data/input/sample.docx"))
        self.assertEqual(paths.output_path, Path("data/output/sample.json"))

    def test_validate_action_paths_rejects_empty_paths(self) -> None:
        with self.assertRaises(PathValidationError):
            validate_action_paths("", "out.json", input_suffix=".docx", output_suffix=".json")

        with self.assertRaises(PathValidationError):
            validate_action_paths("in.docx", "", input_suffix=".docx", output_suffix=".json")

    def test_validate_action_paths_rejects_wrong_extensions(self) -> None:
        with self.assertRaises(PathValidationError):
            validate_action_paths("input.json", "out.json", input_suffix=".docx", output_suffix=".json")

        with self.assertRaises(PathValidationError):
            validate_action_paths("input.docx", "out.docx", input_suffix=".docx", output_suffix=".json")

    @patch("qms_doc_parser.ui.minimal_ui.parse_document")
    def test_dispatch_docx_to_json_calls_backend_function(self, parse_document_mock) -> None:
        output_path = dispatch_docx_to_json("input.docx", "output.json")

        self.assertEqual(output_path, Path("output.json"))
        parse_document_mock.assert_called_once_with(
            input_path=Path("input.docx"),
            output_path=Path("output.json"),
            registry_path=Path("configs/style_registry_adm_tem_011_b.yaml"),
        )

    @patch("qms_doc_parser.ui.minimal_ui.export_review_docx_from_json")
    def test_dispatch_json_to_review_docx_calls_backend_function(self, export_mock) -> None:
        output_path = dispatch_json_to_review_docx("input.json", "review.docx")

        self.assertEqual(output_path, Path("review.docx"))
        export_mock.assert_called_once_with(input_path=Path("input.json"), output_path=Path("review.docx"))


if __name__ == "__main__":
    unittest.main()
