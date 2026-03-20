from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qms_doc_parser.requirements.decompose import build_requirement_records, normalize_requirement_text
from qms_doc_parser.requirements.models import RequirementCandidate


class RequirementDecompositionTests(unittest.TestCase):
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

    def test_single_normative_paragraph_becomes_one_record_with_one_atomic(self) -> None:
        records = build_requirement_records(
            [
                self._candidate(
                    candidate_id="reqc_0001",
                    block_id="b1",
                    text="Специалист должен зарегистрировать продукцию в журнале.",
                    extraction_reason="normative_marker_paragraph",
                )
            ]
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].decomposition_strategy, "single_atomic")
        self.assertEqual(len(records[0].atomic_requirements), 1)
        self.assertEqual(records[0].atomic_requirements[0].atomic_text, "Специалист должен зарегистрировать продукцию в журнале.")

    def test_normative_header_and_contextual_list_items_use_list_based_decomposition(self) -> None:
        records = build_requirement_records(
            [
                self._candidate(candidate_id="reqc_0001", block_id="b1", text="Перечень должен содержать:", extraction_reason="normative_marker_paragraph", section_path=["2"]),
                self._candidate(candidate_id="reqc_0002", block_id="b2", text="- наименование продукции;", extraction_reason="normative_context_list_item", requirement_kind="contextual_obligation", section_path=["2"]),
                self._candidate(candidate_id="reqc_0003", block_id="b3", text="- дату регистрации", extraction_reason="normative_context_list_item", requirement_kind="contextual_obligation", section_path=["2"]),
            ]
        )

        self.assertEqual(records[0].decomposition_strategy, "list_header_context")
        self.assertEqual(records[0].atomic_requirements, [])
        self.assertEqual(records[1].decomposition_strategy, "contextual_list_item")
        self.assertEqual(records[1].atomic_requirements[0].atomic_text, "наименование продукции")
        self.assertEqual(records[2].atomic_requirements[0].atomic_text, "дату регистрации")

    def test_normalization_strips_list_markers_and_trailing_colons_or_semicolons(self) -> None:
        self.assertEqual(normalize_requirement_text("- выполнить проверку;"), "выполнить проверку")
        self.assertEqual(normalize_requirement_text("Организация должна обеспечить:"), "Организация должна обеспечить")

    def test_note_based_candidate_with_obligation_decomposes_safely(self) -> None:
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

        self.assertEqual(records[0].decomposition_strategy, "semicolon_split")
        self.assertEqual(len(records[0].atomic_requirements), 2)
        self.assertEqual(records[0].atomic_requirements[0].source_span_type, "clause")

    def test_multiple_normative_sentences_are_split_into_atomic_requirements(self) -> None:
        records = build_requirement_records(
            [
                self._candidate(
                    candidate_id="reqc_0005",
                    block_id="b5",
                    text="Организация должна вести реестр. Каждый процесс должен пересматриваться ежегодно.",
                    extraction_reason="normative_marker_paragraph",
                    section_path=["5"],
                )
            ]
        )

        self.assertEqual(records[0].decomposition_strategy, "sentence_split")
        self.assertEqual(len(records[0].atomic_requirements), 2)
        self.assertEqual(records[0].atomic_requirements[0].source_span_type, "sentence")

    def test_traceability_fields_are_preserved(self) -> None:
        record = build_requirement_records(
            [
                self._candidate(
                    candidate_id="reqc_0010",
                    block_id="b10",
                    text="Подразделение должно вести журнал учета.",
                    extraction_reason="normative_marker_paragraph",
                    section_path=["4", "4.2"],
                )
            ]
        )[0]

        self.assertEqual(record.source_candidate_id, "reqc_0010")
        self.assertEqual(record.source_block_ids, ["b10"])
        self.assertEqual(record.primary_block_id, "b10")
        self.assertEqual(record.section_path, ["4", "4.2"])
        self.assertEqual(record.atomic_requirements[0].atomic_id, "reqa_0001_01")

    def test_requirement_decomposition_cli_writes_machine_readable_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "requirement_records.json"
            command = [
                sys.executable,
                "scripts/run_requirement_decomposition.py",
                "data/input/1.docx",
                "--registry",
                "configs/style_registry_adm_tem_011_b.yaml",
                "--output",
                str(output_path),
            ]

            result = subprocess.run(command, cwd=Path("/workspace/parser"), capture_output=True, text=True, check=False)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, list)
            if payload:
                self.assertIn("requirement_id", payload[0])
                self.assertIn("source_candidate_id", payload[0])
                self.assertIn("atomic_requirements", payload[0])


if __name__ == "__main__":
    unittest.main()
