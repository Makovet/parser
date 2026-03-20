from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qms_doc_parser.requirements.apply import apply_requirement_review_decisions, classify_requirement_apply_policy
from qms_doc_parser.requirements.decompose import build_requirement_records
from qms_doc_parser.requirements.models import RequirementCandidate, RequirementReviewDecision
from qms_doc_parser.requirements.review import build_requirement_review_cases, build_requirement_review_decisions


class RequirementApplyTests(unittest.TestCase):
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

    def test_contextual_list_item_inherits_subject_from_parent_context(self) -> None:
        records = build_requirement_records(
            [
                self._candidate(candidate_id="reqc_0001", block_id="b1", text="Перечень должен содержать:", extraction_reason="normative_marker_paragraph", section_path=["2"]),
                self._candidate(candidate_id="reqc_0002", block_id="b2", text="- наименование продукции;", extraction_reason="normative_context_list_item", requirement_kind="contextual_obligation", section_path=["2"]),
            ]
        )

        review_cases = build_requirement_review_cases(records)
        review_decisions = build_requirement_review_decisions(review_cases, records)
        applied_records, apply_report = apply_requirement_review_decisions(records, review_decisions)

        self.assertEqual(classify_requirement_apply_policy(review_decisions[1]), "auto_applicable")
        self.assertEqual(applied_records[1].atomic_requirements[0].subject_hint, "Перечень")
        self.assertIn("apply_subject_from_parent_context", applied_records[1].atomic_requirements[0].applied_operations)
        self.assertEqual(apply_report.summary.applied_decisions, 2)

    def test_list_header_context_can_be_preserved_as_context_only(self) -> None:
        records = build_requirement_records(
            [
                self._candidate(candidate_id="reqc_0001", block_id="b1", text="Перечень должен содержать:", extraction_reason="normative_marker_paragraph", section_path=["2"]),
                self._candidate(candidate_id="reqc_0002", block_id="b2", text="- дату регистрации", extraction_reason="normative_context_list_item", requirement_kind="contextual_obligation", section_path=["2"]),
            ]
        )

        review_cases = build_requirement_review_cases(records)
        review_decisions = build_requirement_review_decisions(review_cases, records)
        applied_records, _ = apply_requirement_review_decisions(records, review_decisions)

        self.assertEqual(applied_records[0].atomic_requirements, [])
        self.assertIn("mark_context_only", applied_records[0].applied_operations)
        self.assertEqual(applied_records[0].unresolved_review_flags, [])

    def test_explicit_revised_hints_can_be_applied_safely(self) -> None:
        records = build_requirement_records(
            [
                self._candidate(candidate_id="reqc_0005", block_id="b5", text="Подразделение должно вести журнал учета.", extraction_reason="normative_marker_paragraph", section_path=["4"])
            ]
        )
        decision = RequirementReviewDecision(
            decision_id="reqd_manual_0001",
            review_case_id="reqv_manual_0001",
            requirement_id=records[0].requirement_id,
            decision_label="safe_auto_apply",
            resolution_summary="Apply explicit normalized hints.",
            reviewer_action="apply_hint_cleanup",
            target_atomic_ids=[records[0].atomic_requirements[0].atomic_id],
            revised_subject_hint="Ответственное подразделение",
            revised_action_hint="вести",
            revised_object_hint="журнал учета",
            confidence=0.95,
        )

        applied_records, apply_report = apply_requirement_review_decisions(records, [decision])

        atomic = applied_records[0].atomic_requirements[0]
        self.assertEqual(atomic.subject_hint, "Ответственное подразделение")
        self.assertEqual(atomic.object_hint, "журнал учета")
        self.assertIn("apply_hint_cleanup", atomic.applied_operations)
        self.assertEqual(apply_report.summary.operation_counts["apply_hint_cleanup"], 1)

    def test_unresolved_ambiguous_decision_remains_flagged_without_auto_apply(self) -> None:
        records = build_requirement_records(
            [
                self._candidate(
                    candidate_id="reqc_0004",
                    block_id="b4",
                    text="Примечание. Исполнитель обязан проверить журнал; при выявлении ошибки запись подлежит корректировке.",
                    extraction_reason="normative_marker_note_text",
                    section_path=["3"],
                )
            ]
        )
        review_cases = build_requirement_review_cases(records)
        review_decisions = build_requirement_review_decisions(review_cases, records)

        applied_records, apply_report = apply_requirement_review_decisions(records, review_decisions)

        self.assertEqual(classify_requirement_apply_policy(review_decisions[0]), "requires_human_review")
        self.assertIn("check_condition_attachment", applied_records[0].unresolved_review_flags)
        self.assertEqual(apply_report.summary.unresolved_decisions, 1)
        self.assertEqual(apply_report.summary.applied_decisions, 0)

    def test_traceability_fields_are_preserved_in_applied_output(self) -> None:
        records = build_requirement_records(
            [
                self._candidate(candidate_id="reqc_0010", block_id="b10", text="Подразделение должно вести журнал учета.", extraction_reason="normative_marker_paragraph", section_path=["4", "4.2"])
            ]
        )

        applied_records, _ = apply_requirement_review_decisions(records, [])
        applied_record = applied_records[0]

        self.assertEqual(applied_record.source_requirement_id, records[0].requirement_id)
        self.assertEqual(applied_record.source_candidate_id, "reqc_0010")
        self.assertEqual(applied_record.source_block_ids, ["b10"])
        self.assertEqual(applied_record.primary_block_id, "b10")
        self.assertEqual(applied_record.section_path, ["4", "4.2"])
        self.assertEqual(applied_record.atomic_requirements[0].source_atomic_id, records[0].atomic_requirements[0].atomic_id)

    def test_requirement_apply_cli_writes_machine_readable_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "requirement_apply.json"
            command = [
                sys.executable,
                "scripts/run_requirement_apply.py",
                "data/input/1.docx",
                "--registry",
                "configs/style_registry_adm_tem_011_b.yaml",
                "--output",
                str(output_path),
            ]

            result = subprocess.run(command, cwd=Path("/workspace/parser"), capture_output=True, text=True, check=False)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("applied_requirements", payload)
            self.assertIn("apply_report", payload)
            self.assertIn("summary", payload["apply_report"])


if __name__ == "__main__":
    unittest.main()
