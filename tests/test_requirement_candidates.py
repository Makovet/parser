from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from qms_doc_parser.models.parser_models import BlockType, DocumentZone, ParserBlock, ParserDocument, SectionContext, SourceLocation, SourceMeta
from qms_doc_parser.requirements.extract import extract_requirement_candidates


class RequirementCandidateExtractionTests(unittest.TestCase):
    def _make_block(
        self,
        *,
        block_id: str,
        block_order: int,
        text: str,
        block_type: BlockType = BlockType.paragraph,
        zone: DocumentZone = DocumentZone.main_body,
        section_path: list[str] | None = None,
    ) -> ParserBlock:
        return ParserBlock(
            block_id=block_id,
            block_order=block_order,
            document_zone=zone,
            block_type=block_type,
            normalized_text=text,
            raw_text=text,
            section_context=SectionContext(section_path=section_path or ["1"], section_id=(section_path or ["1"])[-1]),
            source_location=SourceLocation(paragraph_index=block_order),
        )

    def _make_document(self, blocks: list[ParserBlock]) -> ParserDocument:
        return ParserDocument(
            document_id="doc",
            source=SourceMeta(file_name="doc.docx", parser_version="test", processed_at=datetime.utcnow()),
            blocks=blocks,
        )

    def test_main_body_paragraph_with_dolzhen_is_extracted(self) -> None:
        document = self._make_document([
            self._make_block(block_id="b1", block_order=1, text="Специалист должен проверить журнал регистрации.")
        ])

        candidates = extract_requirement_candidates(document)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].primary_block_id, "b1")
        self.assertEqual(candidates[0].source_block_ids, ["b1"])
        self.assertEqual(candidates[0].document_zone, DocumentZone.main_body.value)
        self.assertEqual(candidates[0].extraction_reason, "normative_marker_paragraph")

    def test_list_item_in_normative_context_is_extracted(self) -> None:
        document = self._make_document(
            [
                self._make_block(block_id="b1", block_order=1, text="Организация должна выполнять следующие действия:", section_path=["2"]),
                self._make_block(block_id="b2", block_order=2, text="проверять комплектность документов", block_type=BlockType.list_item, section_path=["2"]),
                self._make_block(block_id="b3", block_order=3, text="согласовывать отклонения", block_type=BlockType.list_item, section_path=["2"]),
            ]
        )

        candidates = extract_requirement_candidates(document)

        self.assertEqual([candidate.primary_block_id for candidate in candidates], ["b1", "b2", "b3"])
        self.assertEqual(candidates[1].extraction_reason, "normative_context_list_item")
        self.assertEqual(candidates[2].extraction_reason, "normative_context_list_item")

    def test_narrative_main_body_paragraph_without_normative_markers_is_not_extracted(self) -> None:
        document = self._make_document([
            self._make_block(block_id="b1", block_order=1, text="Настоящая процедура описывает общую схему взаимодействия подразделений.")
        ])

        candidates = extract_requirement_candidates(document)

        self.assertEqual(candidates, [])

    def test_appendix_block_with_normative_text_is_out_of_scope(self) -> None:
        document = self._make_document([
            self._make_block(
                block_id="b1",
                block_order=1,
                text="Исполнитель должен заполнить форму приложения.",
                zone=DocumentZone.appendix,
                section_path=["А"],
            )
        ])

        candidates = extract_requirement_candidates(document)

        self.assertEqual(candidates, [])

    def test_title_control_sheet_and_toc_blocks_are_out_of_scope(self) -> None:
        document = self._make_document(
            [
                self._make_block(block_id="b1", block_order=1, text="Организация должна ...", zone=DocumentZone.title_page, section_path=[]),
                self._make_block(block_id="b2", block_order=2, text="Организация должна ...", zone=DocumentZone.control_sheet, section_path=[]),
                self._make_block(block_id="b3", block_order=3, text="Организация должна ...", zone=DocumentZone.toc, section_path=[]),
            ]
        )

        candidates = extract_requirement_candidates(document)

        self.assertEqual(candidates, [])

    def test_traceability_fields_are_populated(self) -> None:
        document = self._make_document([
            self._make_block(block_id="b7", block_order=7, text="Подразделение обязано вести учет записей.", section_path=["3", "3.1"])
        ])

        candidates = extract_requirement_candidates(document)

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.primary_block_id, "b7")
        self.assertEqual(candidate.source_block_ids, ["b7"])
        self.assertEqual(candidate.section_path, ["3", "3.1"])
        self.assertEqual(candidate.compact_section_path, "3 > 3.1")
        self.assertEqual(candidate.candidate_text, "Подразделение обязано вести учет записей.")

    def test_requirement_candidates_cli_writes_machine_readable_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "requirements.json"
            command = [
                sys.executable,
                "scripts/run_requirement_candidates.py",
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
                self.assertIn("candidate_id", payload[0])
                self.assertIn("primary_block_id", payload[0])
                self.assertIn("source_block_ids", payload[0])


if __name__ == "__main__":
    unittest.main()
