from __future__ import annotations

import unittest

from qms_doc_parser.models.parser_models import (
    BlockFlags,
    BlockType,
    DocumentZone,
    HeadingInfo,
    ParserBlock,
    SectionContext,
)
from qms_doc_parser.review.block_features import annotate_blocks_for_review
from qms_doc_parser.review.review_candidates import build_review_candidates


class ReviewCandidateTests(unittest.TestCase):
    def _make_block(
        self,
        *,
        block_id: str,
        block_order: int,
        block_type: BlockType,
        text: str | None = None,
        zone: DocumentZone = DocumentZone.main_body,
        block_subtype: str | None = None,
        heading_info: HeadingInfo | None = None,
        section_path: list[str] | None = None,
        flags: BlockFlags | None = None,
        metadata: dict | None = None,
    ) -> ParserBlock:
        return ParserBlock(
            block_id=block_id,
            block_order=block_order,
            document_zone=zone,
            block_type=block_type,
            block_subtype=block_subtype,
            raw_text=text,
            normalized_text=text,
            heading_info=heading_info,
            section_context=SectionContext(section_path=section_path or []),
            flags=flags or BlockFlags(),
            metadata=metadata,
        )

    def test_block_review_features_are_annotated_stably(self) -> None:
        blocks = [
            self._make_block(
                block_id="b1",
                block_order=1,
                block_type=BlockType.heading,
                text="Требования:",
                heading_info=HeadingInfo(detection_method="text_fallback"),
                section_path=["1", "1.1"],
            ),
            self._make_block(
                block_id="b2",
                block_order=2,
                block_type=BlockType.list_item,
                text="- Элемент списка",
                section_path=["1", "1.1"],
            ),
        ]

        annotate_blocks_for_review(blocks)

        first = blocks[0]
        self.assertEqual(first.next_block_id, "b2")
        self.assertIsNone(first.prev_block_id)
        self.assertIsNotNone(first.review_features)
        self.assertEqual(first.review_features.compact_section_path, "1 > 1.1")
        self.assertEqual(first.review_features.heading_detection_source, "fallback")
        self.assertTrue(first.review_features.text_ends_with_colon)
        self.assertTrue(first.review_features.next_blocks_are_list_items)
        self.assertFalse(first.review_features.is_empty_or_layout_artifact)

    def test_heading_with_colon_followed_by_list_becomes_review_candidate(self) -> None:
        blocks = [
            self._make_block(
                block_id="b1",
                block_order=1,
                block_type=BlockType.heading,
                text="Обязательные документы:",
                heading_info=HeadingInfo(detection_method="style_registry"),
            ),
            self._make_block(
                block_id="b2",
                block_order=2,
                block_type=BlockType.list_item,
                text="- Процедура",
            ),
        ]

        annotate_blocks_for_review(blocks)
        candidates = build_review_candidates(blocks)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].block_id, "b1")
        self.assertIn("heading_with_colon_before_list", candidates[0].reason_codes)

    def test_figure_with_table_like_text_becomes_review_candidate(self) -> None:
        blocks = [
            self._make_block(
                block_id="b1",
                block_order=1,
                block_type=BlockType.figure,
                text="Таблица 1 — План аудита",
            )
        ]

        annotate_blocks_for_review(blocks)
        candidates = build_review_candidates(blocks)

        self.assertEqual(len(candidates), 1)
        self.assertIn("figure_text_looks_like_table", candidates[0].reason_codes)

    def test_orphan_note_becomes_review_candidate(self) -> None:
        blocks = [
            self._make_block(
                block_id="b1",
                block_order=1,
                block_type=BlockType.note_text,
                text="Примечание — текст без пары",
                metadata={"is_orphan": True, "note_role": "text"},
            )
        ]

        annotate_blocks_for_review(blocks)
        candidates = build_review_candidates(blocks)

        self.assertEqual(len(candidates), 1)
        self.assertIn("orphan_note", candidates[0].reason_codes)

    def test_clean_heading_and_paragraph_do_not_create_candidates(self) -> None:
        blocks = [
            self._make_block(
                block_id="b1",
                block_order=1,
                block_type=BlockType.heading,
                text="Назначение",
                heading_info=HeadingInfo(detection_method="style_registry"),
            ),
            self._make_block(
                block_id="b2",
                block_order=2,
                block_type=BlockType.paragraph,
                text="Настоящая процедура устанавливает порядок проведения аудитов.",
            ),
        ]

        annotate_blocks_for_review(blocks)
        candidates = build_review_candidates(blocks)

        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
