from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qms_doc_parser.requirements.models import RequirementCandidate
from qms_doc_parser.requirements.decompose import build_requirement_records
from qms_doc_parser.requirements.review import build_requirement_review_cases, build_requirement_review_decisions


class RequirementReviewTests(unittest.TestCase):
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

    def test_list_header_and_contextual_items_become_review_cases_without_auto_apply(self) -> None:
        records = build_requirement_records(
            [
                self._candidate(candidate_id="reqc_0001", block_id="b1", text="Перечень должен содержать:", extraction_reason="normative_marker_paragraph", section_path=["2"]),
                self._candidate(candidate_id="reqc_0002", block_id="b2", text="- наименование продукции;", extraction_reason="normative_context_list_item", requirement_kind="contextual_obligation", section_path=["2"]),
                self._candidate(candidate_id="reqc_0003", block_id="b3", text="- дату регистрации", extraction_reason="normative_context_list_item", requirement_kind="contextual_obligation", section_path=["2"]),
            ]
        )

        review_cases = build_requirement_review_cases(records)
        decisions = build_requirement_review_decisions(review_cases, records)

        self.assertEqual([case.ambiguity_type for case in review_cases], ["requires_list_item_context", "missing_subject_context", "missing_subject_context"])
        self.assertEqual(review_cases[0].context_requirement_ids, ["reqr_0002", "reqr_0003"])
        self.assertEqual(decisions[0].decision_label, "safe_auto_apply")
        self.assertEqual(decisions[0].reviewer_action, "mark_context_only")
        self.assertEqual(records[0].atomic_requirements, [])

    def test_conditional_semicolon_split_gets_review_recommended_decision(self) -> None:
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
        decisions = build_requirement_review_decisions(review_cases, records)

        self.assertEqual(len(review_cases), 1)
        self.assertEqual(review_cases[0].ambiguity_type, "conditional_clause_scope")
        self.assertEqual(decisions[0].decision_label, "review_recommended")
        self.assertEqual(decisions[0].reviewer_action, "check_condition_attachment")

    def test_requirement_review_cli_writes_machine_readable_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "requirement_review.json"
            command = [
                sys.executable,
                "scripts/run_requirement_review.py",
                "data/input/1.docx",
                "--registry",
                "configs/style_registry_adm_tem_011_b.yaml",
                "--output",
                str(output_path),
            ]

            result = subprocess.run(command, cwd=Path("/workspace/parser"), capture_output=True, text=True, check=False)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("review_cases", payload)
            self.assertIn("review_decisions", payload)
            if payload["review_cases"]:
                self.assertIn("review_case_id", payload["review_cases"][0])
                self.assertIn("ambiguity_type", payload["review_cases"][0])


if __name__ == "__main__":
    unittest.main()
