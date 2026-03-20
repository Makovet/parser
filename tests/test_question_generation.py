from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qms_doc_parser.questions.generate import classify_question_generation_eligibility, generate_audit_questions
from qms_doc_parser.requirements.apply import apply_requirement_review_decisions
from qms_doc_parser.requirements.decompose import build_requirement_records
from qms_doc_parser.requirements.models import RequirementCandidate
from qms_doc_parser.requirements.review import build_requirement_review_cases, build_requirement_review_decisions


class QuestionGenerationTests(unittest.TestCase):
    def _candidate(
        self,
        *,
        candidate_id: str,
        text: str,
        extraction_reason: str,
        requirement_kind: str | None = "obligation",
        section_path: list[str] | None = None,
        block_id: str | None = None,
    ) -> RequirementCandidate:
        return RequirementCandidate(
            candidate_id=candidate_id,
            source_block_ids=[block_id or candidate_id],
            primary_block_id=block_id or candidate_id,
            section_path=section_path or ["1"],
            document_zone="main_body",
            candidate_text=text,
            extraction_reason=extraction_reason,
            confidence=0.9,
            requirement_kind=requirement_kind,
            compact_section_path=" > ".join(section_path or ["1"]),
        )

    def _build_applied_records(self, candidates: list[RequirementCandidate]):
        records = build_requirement_records(candidates)
        review_cases = build_requirement_review_cases(records)
        review_decisions = build_requirement_review_decisions(review_cases, records)
        return apply_requirement_review_decisions(records, review_decisions)

    def test_safe_atomic_obligation_generates_one_question(self) -> None:
        applied_records, _ = self._build_applied_records(
            [
                self._candidate(
                    candidate_id="reqc_0001",
                    block_id="b1",
                    text="Специалист должен зарегистрировать продукцию в журнале.",
                    extraction_reason="normative_marker_paragraph",
                )
            ]
        )

        report = generate_audit_questions(applied_records)

        self.assertEqual(report.summary.total_questions, 1)
        self.assertEqual(report.questions[0].question_type, "evidence_check")
        self.assertIn("Как подтверждается", report.questions[0].question_text)

    def test_contextual_list_item_after_safe_apply_generates_one_question(self) -> None:
        applied_records, _ = self._build_applied_records(
            [
                self._candidate(candidate_id="reqc_0001", block_id="b1", text="Перечень должен содержать:", extraction_reason="normative_marker_paragraph", section_path=["2"]),
                self._candidate(candidate_id="reqc_0002", block_id="b2", text="- дату регистрации", extraction_reason="normative_context_list_item", requirement_kind="contextual_obligation", section_path=["2"]),
            ]
        )

        report = generate_audit_questions(applied_records)

        self.assertEqual(report.summary.total_questions, 1)
        self.assertEqual(report.summary.skipped_context_only, 1)
        self.assertIn("дату регистрации", report.questions[0].question_text.lower())

    def test_unresolved_atomic_is_skipped(self) -> None:
        applied_records, _ = self._build_applied_records(
            [
                self._candidate(
                    candidate_id="reqc_0003",
                    block_id="b3",
                    text="Примечание. Исполнитель обязан проверить журнал; при выявлении ошибки запись подлежит корректировке.",
                    extraction_reason="normative_marker_note_text",
                    section_path=["3"],
                )
            ]
        )

        report = generate_audit_questions(applied_records)

        self.assertEqual(report.summary.total_questions, 0)
        self.assertEqual(report.summary.skipped_unresolved, 2)

    def test_context_only_requirement_is_skipped_as_question_target(self) -> None:
        applied_records, _ = self._build_applied_records(
            [
                self._candidate(candidate_id="reqc_0001", block_id="b1", text="Перечень должен содержать:", extraction_reason="normative_marker_paragraph", section_path=["2"]),
                self._candidate(candidate_id="reqc_0002", block_id="b2", text="- дату регистрации", extraction_reason="normative_context_list_item", requirement_kind="contextual_obligation", section_path=["2"]),
            ]
        )

        eligible, reason = classify_question_generation_eligibility(applied_records[1], applied_records[1].atomic_requirements[0])
        self.assertTrue(eligible)
        self.assertIsNone(reason)
        report = generate_audit_questions(applied_records)
        self.assertEqual(report.summary.skipped_context_only, 1)

    def test_traceability_fields_are_preserved(self) -> None:
        applied_records, _ = self._build_applied_records(
            [
                self._candidate(
                    candidate_id="reqc_0010",
                    block_id="b10",
                    text="Подразделение должно вести журнал учета.",
                    extraction_reason="normative_marker_paragraph",
                    section_path=["4", "4.2"],
                )
            ]
        )

        report = generate_audit_questions(applied_records)
        question = report.questions[0]

        self.assertEqual(question.source_applied_requirement_id, applied_records[0].applied_requirement_id)
        self.assertEqual(question.source_atomic_id, applied_records[0].atomic_requirements[0].source_atomic_id)
        self.assertEqual(question.source_requirement_id, applied_records[0].source_requirement_id)
        self.assertEqual(question.source_candidate_id, "reqc_0010")
        self.assertEqual(question.source_block_ids, ["b10"])

    def test_summary_counts_are_machine_readable(self) -> None:
        applied_records, _ = self._build_applied_records(
            [
                self._candidate(candidate_id="reqc_0001", block_id="b1", text="Перечень должен содержать:", extraction_reason="normative_marker_paragraph", section_path=["2"]),
                self._candidate(candidate_id="reqc_0002", block_id="b2", text="- дату регистрации", extraction_reason="normative_context_list_item", requirement_kind="contextual_obligation", section_path=["2"]),
                self._candidate(candidate_id="reqc_0003", block_id="b3", text="Специалист должен зарегистрировать продукцию в журнале.", extraction_reason="normative_marker_paragraph", section_path=["2"]),
            ]
        )

        report = generate_audit_questions(applied_records)

        self.assertEqual(report.summary.total_questions, 2)
        self.assertEqual(report.summary.generated_from_safe_atomic, 2)
        self.assertEqual(report.summary.skipped_context_only, 1)
        self.assertIn("evidence_check", report.summary.question_type_counts)

    def test_question_generation_cli_writes_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "audit_questions.json"
            command = [
                sys.executable,
                "scripts/run_question_generation.py",
                "data/input/1.docx",
                "--registry",
                "configs/style_registry_adm_tem_011_b.yaml",
                "--output",
                str(output_path),
            ]

            result = subprocess.run(command, cwd=Path("/workspace/parser"), capture_output=True, text=True, check=False)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("questions", payload)
            self.assertIn("summary", payload)
            self.assertIn("total_questions", payload["summary"])


if __name__ == "__main__":
    unittest.main()
