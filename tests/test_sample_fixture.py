from __future__ import annotations

import json
import unittest
from pathlib import Path

from qms_doc_parser.pipeline.parser_pipeline import parse_docx_to_document


class SampleFixtureTests(unittest.TestCase):
    def test_sample_docx_matches_expected_fixture(self) -> None:
        input_path = Path("data/input/1.docx")
        registry_path = Path("configs/style_registry_adm_tem_011_b.yaml")
        expected_path = Path("tests/fixtures/expected/1.json")

        parsed = parse_docx_to_document(input_path=input_path, registry_path=registry_path)
        actual = parsed.model_dump(mode="json", exclude_none=True)
        expected = json.loads(expected_path.read_text(encoding="utf-8"))

        self.assertEqual(actual["document_id"], expected["document_id"])
        self.assertEqual(actual["template_id"], expected["template_id"])
        self.assertEqual(actual["source"]["file_name"], expected["source"]["file_name"])
        self.assertEqual(actual["source"]["file_type"], expected["source"]["file_type"])
        self.assertEqual(actual["source"]["parser_version"], expected["source"]["parser_version"])
        self.assertEqual(actual["source"]["language"], expected["source"]["language"])
        self.assertEqual(actual["document_metadata"], expected["document_metadata"])
        self.assertEqual(actual["structure_summary"], expected["structure_summary"])
        self.assertEqual(actual["style_registry_used"], expected["style_registry_used"])
        self.assertEqual(actual["blocks"], expected["blocks"])
        self.assertIsInstance(actual["source"]["processed_at"], str)
        self.assertIsInstance(expected["source"]["processed_at"], str)


if __name__ == "__main__":
    unittest.main()
