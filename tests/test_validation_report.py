from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qms_doc_parser.models.parser_models import (
    BlockFlags,
    BlockReviewFeatures,
    BlockType,
    DocumentZone,
    ParserBlock,
    ParserDocument,
    SectionContext,
    SourceLocation,
    SourceMeta,
    StructureSummary,
)
from qms_doc_parser.validation.report import validate_parser_output


class ValidationReportTests(unittest.TestCase):
    def test_sample_doc_produces_downstream_ready_validation_report(self) -> None:
        from qms_doc_parser.pipeline.parser_pipeline import parse_docx_to_document

        parsed = parse_docx_to_document(
            input_path=Path("data/input/1.docx"),
            registry_path=Path("configs/style_registry_adm_tem_011_b.yaml"),
        )

        report = validate_parser_output(parsed)

        self.assertTrue(report.downstream_ready)
        self.assertEqual(report.metrics["failed_checks"], 0)
        self.assertGreater(report.metrics["total_blocks"], 0)
        self.assertTrue(any(check.name == "review_candidates_build" for check in report.checks))
        self.assertTrue(any(spec.path == "ParserBlock.review_features" for spec in report.parser_contract))

    def test_intentionally_broken_document_fails_validation(self) -> None:
        broken_block = ParserBlock(
            block_id="b1",
            block_order=1,
            document_zone=DocumentZone.main_body,
            block_type=BlockType.table,
            raw_text=None,
            normalized_text=None,
            section_context=SectionContext(section_id="1", section_path=["broken"]),
            source_location=SourceLocation(table_index=1),
            flags=BlockFlags(),
            review_features=BlockReviewFeatures(),
            prev_block_id="b999",
            next_block_id=None,
        )
        broken_document = ParserDocument(
            document_id="broken",
            template_id="ADM-TEM-011_B",
            source=SourceMeta(file_name="broken.docx", parser_version="test", processed_at=parsed_datetime()),
            structure_summary=StructureSummary(total_blocks=1, total_tables=0, total_sections=0),
            blocks=[broken_block],
        )

        report = validate_parser_output(broken_document)

        self.assertFalse(report.downstream_ready)
        failed = {check.name for check in report.checks if check.status.value == "failed"}
        self.assertIn("structure_summary_consistency", failed)
        self.assertIn("adjacent_block_links", failed)
        self.assertIn("table_block_payloads", failed)
        self.assertIn("section_context_validity", failed)

    def test_validation_cli_preserves_review_candidates_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "validation.json"
            command = [
                sys.executable,
                "scripts/run_validation_report.py",
                "data/input/1.docx",
                "--registry",
                "configs/style_registry_adm_tem_011_b.yaml",
                "--output",
                str(output_path),
            ]

            result = subprocess.run(command, cwd=Path("/workspace/parser"), capture_output=True, text=True, check=False)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["downstream_ready"])
            check_names = {check["name"] for check in payload["checks"]}
            self.assertIn("review_candidates_build", check_names)
            self.assertIn("review_candidates_links", check_names)


def parsed_datetime():
    from datetime import datetime

    return datetime.utcnow()


if __name__ == "__main__":
    unittest.main()
