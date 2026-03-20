from __future__ import annotations

import unittest
from pathlib import Path

from qms_doc_parser.classifiers.style_classifier import ClassificationInput, StyleClassifier
from qms_doc_parser.models.parser_models import BlockType, DocumentZone
from qms_doc_parser.registry.registry_loader import load_style_registry
from qms_doc_parser.trackers.section_tracker import SectionTracker


REGISTRY_PATH = Path("configs/style_registry_adm_tem_011_b.yaml")


class StructureDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.classifier = StyleClassifier(load_style_registry(REGISTRY_PATH))

    def test_heading_styles_are_classified_as_headings(self) -> None:
        heading_1 = self.classifier.classify(
            ClassificationInput(
                block_id="b1",
                block_order=1,
                text="Назначение",
                style_name="Heading 1",
                current_zone=DocumentZone.toc.value,
            )
        )
        heading_2 = self.classifier.classify(
            ClassificationInput(
                block_id="b2",
                block_order=2,
                text="Цели внутреннего аудита",
                style_name="Heading 2",
                current_zone=DocumentZone.main_body.value,
            )
        )

        self.assertEqual(heading_1.block_type, BlockType.heading)
        self.assertEqual(heading_1.document_zone, DocumentZone.main_body)
        self.assertEqual(heading_1.heading_info.heading_level, 1)
        self.assertEqual(heading_2.block_type, BlockType.heading)
        self.assertEqual(heading_2.heading_info.heading_level, 2)

    def test_appendix_heading_is_detected_by_style_and_text(self) -> None:
        by_style = self.classifier.classify(
            ClassificationInput(
                block_id="b1",
                block_order=1,
                text="Приложение А Форма записи",
                style_name="Заголовок 7;Прил. A",
                current_zone=DocumentZone.main_body.value,
            )
        )
        by_text = self.classifier.classify(
            ClassificationInput(
                block_id="b2",
                block_order=2,
                text="Приложение Б Перечень документов",
                style_name="Heading 1",
                current_zone=DocumentZone.main_body.value,
            )
        )

        self.assertEqual(by_style.block_type, BlockType.appendix_heading)
        self.assertEqual(by_style.document_zone, DocumentZone.appendix)
        self.assertEqual(by_style.heading_info.heading_number, "А")
        self.assertEqual(by_text.block_type, BlockType.appendix_heading)
        self.assertEqual(by_text.document_zone, DocumentZone.appendix)
        self.assertEqual(by_text.heading_info.heading_number, "Б")

    def test_zone_transitions_follow_front_matter_main_body_and_appendix(self) -> None:
        current_zone = DocumentZone.title_page.value
        tracker = SectionTracker()
        sequence = [
            ("Титул документа", "0_ИЦЖТ_Титульный_Заголовки", BlockType.title_meta, DocumentZone.title_page),
            ("Контрольный лист", "0_ИЦЖТ_Заголовок_Структурный (вне содержания)", BlockType.heading, DocumentZone.control_sheet),
            ("Содержание", "0_ИЦЖТ_Заголовок_Структурный (вне содержания)", BlockType.heading, DocumentZone.toc),
            ("1 Общие положения", "Heading 1", BlockType.heading, DocumentZone.main_body),
            ("Приложение А Форма записи", "Heading 1", BlockType.appendix_heading, DocumentZone.appendix),
        ]

        observed = []
        for order, (text, style_name, expected_type, expected_zone) in enumerate(sequence, start=1):
            block = self.classifier.classify(
                ClassificationInput(
                    block_id=f"b{order}",
                    block_order=order,
                    text=text,
                    style_name=style_name,
                    current_zone=current_zone,
                )
            )
            block = tracker.apply(block)
            observed.append(block)
            if block.document_zone != DocumentZone.unknown_zone:
                current_zone = block.document_zone.value
            self.assertEqual(block.block_type, expected_type)
            self.assertEqual(block.document_zone, expected_zone)

        self.assertEqual(observed[3].section_context.section_id, "1")
        self.assertEqual(observed[4].section_context.section_id, "А")

    def test_section_context_inherits_to_following_blocks(self) -> None:
        tracker = SectionTracker()
        current_zone = DocumentZone.title_page.value
        blocks = []
        inputs = [
            ("1 Общие положения", "Heading 1"),
            ("Текст раздела", "0_ИЦЖТ_Текст"),
            ("1.1 Подраздел", "Heading 2"),
            ("Текст подраздела", "0_ИЦЖТ_Текст"),
            ("Приложение А Форма записи", "Heading 1"),
            ("Текст приложения", "0_ИЦЖТ_Текст"),
        ]

        for order, (text, style_name) in enumerate(inputs, start=1):
            block = self.classifier.classify(
                ClassificationInput(
                    block_id=f"b{order}",
                    block_order=order,
                    text=text,
                    style_name=style_name,
                    current_zone=current_zone,
                )
            )
            if block.document_zone != DocumentZone.unknown_zone:
                current_zone = block.document_zone.value
            blocks.append(tracker.apply(block))

        self.assertEqual(blocks[1].section_context.section_path, ["1"])
        self.assertEqual(blocks[3].section_context.section_path, ["1", "1.1"])
        self.assertEqual(blocks[4].section_context.section_path, ["А"])
        self.assertEqual(blocks[5].section_context.section_path, ["А"])

    def test_regression_non_headings_remain_non_headings(self) -> None:
        table_caption = self.classifier.classify(
            ClassificationInput(
                block_id="b1",
                block_order=1,
                text="Таблица 1 — План аудита",
                style_name="01_ИЦЖТ_таблица_названия",
                current_zone=DocumentZone.main_body.value,
            )
        )
        ordinary_paragraph = self.classifier.classify(
            ClassificationInput(
                block_id="b2",
                block_order=2,
                text="Настоящая процедура применяется во всех подразделениях.",
                style_name="0_ИЦЖТ_Текст",
                current_zone=DocumentZone.main_body.value,
            )
        )

        self.assertEqual(table_caption.block_type, BlockType.table_caption)
        self.assertEqual(ordinary_paragraph.block_type, BlockType.paragraph)


if __name__ == "__main__":
    unittest.main()
