from __future__ import annotations

import unittest
from pathlib import Path

from qms_doc_parser.models.parser_models import BlockType, DocumentZone
from qms_doc_parser.pipeline.parser_pipeline import parse_docx_to_document


class SampleIntegrationTests(unittest.TestCase):
    def test_sample_docx_preserves_key_parser_invariants(self) -> None:
        parsed = parse_docx_to_document(
            input_path=Path("data/input/1.docx"),
            registry_path=Path("configs/style_registry_adm_tem_011_b.yaml"),
        )

        self.assertEqual(parsed.document_id, "1")
        self.assertEqual(parsed.template_id, "ADM-TEM-011_B")
        self.assertGreater(parsed.structure_summary.total_blocks, 0)
        self.assertGreater(parsed.structure_summary.total_sections, 0)
        self.assertGreater(parsed.structure_summary.total_tables, 0)
        self.assertIn("Heading 1", parsed.style_registry_used)
        self.assertIn("Heading 2", parsed.style_registry_used)
        self.assertIn("Normal", parsed.style_registry_used)

        zones = {block.document_zone for block in parsed.blocks}
        self.assertIn(DocumentZone.title_page, zones)
        self.assertIn(DocumentZone.control_sheet, zones)
        self.assertIn(DocumentZone.main_body, zones)
        self.assertIn(DocumentZone.bibliography, zones)

        headings = [block for block in parsed.blocks if block.block_type == BlockType.heading]
        self.assertGreaterEqual(len(headings), 10)
        self.assertTrue(any(block.heading_info and block.heading_info.heading_level == 1 for block in headings))
        self.assertTrue(any(block.heading_info and block.heading_info.heading_level == 2 for block in headings))
        self.assertTrue(any(block.section_context.section_path for block in headings))

        tables = [block for block in parsed.blocks if block.block_type == BlockType.table]
        self.assertEqual(parsed.structure_summary.total_tables, len(tables))
        self.assertTrue(all(block.table_info is not None for block in tables))

        suspicious_blocks = [block for block in parsed.blocks if block.flags.is_suspicious or block.flags.needs_review]
        suspicious_styles = {block.source_style for block in suspicious_blocks}
        self.assertFalse({"Heading 1", "Heading 2", "Normal"} & suspicious_styles)
        self.assertFalse({"0_ИЦЖТ_Заголовок_Структурный", "0_ИЦЖТ_Заголовок_Структурный (вне содержания)"} & suspicious_styles)


if __name__ == "__main__":
    unittest.main()
