from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qms_doc_parser.validation.batch import aggregate_batch_results, build_batch_validation_report, discover_docx_inputs
from qms_doc_parser.validation.models import BatchValidationDocumentResult, ValidationCheckResult, ValidationReport, ValidationStatus


class ValidationBatchTests(unittest.TestCase):
    def test_aggregate_multiple_reports_counts_passed_failed_and_warnings(self) -> None:
        passed_report = ValidationReport(
            document_id="good",
            downstream_ready=True,
            checks=[ValidationCheckResult(name="non_empty_document", status=ValidationStatus.passed, message="ok")],
        )
        failed_report = ValidationReport(
            document_id="bad",
            downstream_ready=False,
            checks=[
                ValidationCheckResult(name="adjacent_block_links", status=ValidationStatus.failed, message="broken links"),
                ValidationCheckResult(name="note_block_review_readiness", status=ValidationStatus.warning, message="warn"),
            ],
        )

        summary = aggregate_batch_results(
            [
                BatchValidationDocumentResult(
                    input_path="good.docx",
                    report=passed_report,
                    status=ValidationStatus.passed,
                    message="ok",
                ),
                BatchValidationDocumentResult(
                    input_path="bad.docx",
                    report=failed_report,
                    status=ValidationStatus.failed,
                    message="failed",
                ),
                BatchValidationDocumentResult(
                    input_path="missing.docx",
                    status=ValidationStatus.warning,
                    message="missing",
                ),
            ]
        )

        self.assertEqual(summary.total_documents, 3)
        self.assertEqual(summary.passed_documents, 1)
        self.assertEqual(summary.failed_documents, 1)
        self.assertEqual(summary.warnings_count, 2)
        self.assertEqual(summary.common_failed_checks, {"adjacent_block_links": 1})
        self.assertEqual(summary.common_warning_checks, {"input_discovery": 1, "note_block_review_readiness": 1})

    def test_build_batch_validation_report_handles_empty_input_repeatably(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            report = build_batch_validation_report(
                [],
                registry_path="configs/style_registry_adm_tem_011_b.yaml",
                reports_dir=Path(tmp_dir) / "reports",
            )

        self.assertEqual(report.summary.total_documents, 1)
        self.assertEqual(report.summary.passed_documents, 0)
        self.assertEqual(report.summary.failed_documents, 0)
        self.assertEqual(report.summary.warnings_count, 1)
        self.assertEqual(report.summary.common_warning_checks, {"input_discovery": 1})
        self.assertEqual(report.documents[0].message, "No DOCX inputs were discovered for batch validation.")

    def test_discover_docx_inputs_marks_invalid_path(self) -> None:
        discovered, issues = discover_docx_inputs(["/definitely/missing.docx"])

        self.assertEqual(discovered, [])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].status, ValidationStatus.failed)
        self.assertIn("does not exist", issues[0].message)

    def test_batch_cli_writes_machine_readable_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            reports_dir = tmp_path / "reports"
            summary_output = tmp_path / "summary.json"
            command = [
                sys.executable,
                "scripts/run_validation_batch.py",
                "data/input/1.docx",
                "--registry",
                "configs/style_registry_adm_tem_011_b.yaml",
                "--reports-dir",
                str(reports_dir),
                "--summary-output",
                str(summary_output),
            ]

            result = subprocess.run(command, cwd=Path("/workspace/parser"), capture_output=True, text=True, check=False)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(summary_output.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["total_documents"], 1)
            self.assertEqual(payload["summary"]["passed_documents"], 1)
            self.assertEqual(payload["summary"]["failed_documents"], 0)
            self.assertIsInstance(payload["documents"], list)
            self.assertTrue(payload["documents"][0]["report_path"])


if __name__ == "__main__":
    unittest.main()
