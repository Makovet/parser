from __future__ import annotations

import unittest

from qms_doc_parser.models.parser_models import BlockType, DocumentZone, ParserBlock
from qms_doc_parser.parsers.note_parser import apply_note_grouping
from qms_doc_parser.pipeline.parser_pipeline import _count_logical_notes


class NoteParserTests(unittest.TestCase):
    def _make_block(
        self,
        *,
        block_id: str,
        block_order: int,
        source_style: str | None,
        block_subtype: str | None,
        zone: DocumentZone = DocumentZone.main_body,
        block_type: BlockType = BlockType.note_like,
        metadata: dict | None = None,
    ) -> ParserBlock:
        return ParserBlock(
            block_id=block_id,
            block_order=block_order,
            document_zone=zone,
            block_type=block_type,
            block_subtype=block_subtype,
            raw_text="raw",
            normalized_text="normalized",
            source_style=source_style,
            metadata={"existing": "value", **(metadata or {})},
        )

    def test_pairs_adjacent_note_label_and_note_text_in_same_zone(self) -> None:
        label = self._make_block(
            block_id="b1",
            block_order=1,
            source_style="05_ИЦЖТ_Примечание_слово",
            block_subtype="note_label",
        )
        text = self._make_block(
            block_id="b2",
            block_order=2,
            source_style="05_ИЦЖТ_Примечание_текст после",
            block_subtype="note_text",
        )

        blocks = [label, text]
        apply_note_grouping(blocks)

        self.assertEqual(label.block_type, BlockType.note_label)
        self.assertEqual(text.block_type, BlockType.note_text)
        self.assertEqual(label.metadata["note_group_id"], text.metadata["note_group_id"])
        self.assertEqual(label.metadata["note_group_id"], "note_group_0001")
        self.assertFalse(label.metadata["is_orphan"])
        self.assertFalse(text.metadata["is_orphan"])
        self.assertEqual(label.metadata["note_role"], "label")
        self.assertEqual(text.metadata["note_role"], "text")
        self.assertEqual(label.metadata["existing"], "value")
        self.assertEqual(text.metadata["existing"], "value")

    def test_marks_orphan_note_label(self) -> None:
        label = self._make_block(
            block_id="b1",
            block_order=1,
            source_style="05_ИЦЖТ_Примечание_слово",
            block_subtype="note_label",
        )

        blocks = [label]
        apply_note_grouping(blocks)

        self.assertEqual(label.block_type, BlockType.note_label)
        self.assertTrue(label.metadata["is_orphan"])
        self.assertIsNone(label.metadata["note_group_id"])
        self.assertEqual(label.metadata["note_role"], "label")

    def test_marks_orphan_note_text(self) -> None:
        text = self._make_block(
            block_id="b1",
            block_order=1,
            source_style="05_ИЦЖТ_Примечание_текст после",
            block_subtype="note_text",
        )

        blocks = [text]
        apply_note_grouping(blocks)

        self.assertEqual(text.block_type, BlockType.note_text)
        self.assertTrue(text.metadata["is_orphan"])
        self.assertIsNone(text.metadata["note_group_id"])
        self.assertEqual(text.metadata["note_role"], "text")

    def test_label_paragraph_text_do_not_pair(self) -> None:
        label = self._make_block(
            block_id="b1",
            block_order=1,
            source_style="05_ИЦЖТ_Примечание_слово",
            block_subtype="note_label",
        )
        paragraph = self._make_block(
            block_id="b2",
            block_order=2,
            source_style="0_ИЦЖТ_Текст",
            block_subtype="main_text",
            block_type=BlockType.paragraph,
        )
        text = self._make_block(
            block_id="b3",
            block_order=3,
            source_style="05_ИЦЖТ_Примечание_текст после",
            block_subtype="note_text",
        )

        blocks = [label, paragraph, text]
        apply_note_grouping(blocks)

        self.assertTrue(label.metadata["is_orphan"])
        self.assertTrue(text.metadata["is_orphan"])
        self.assertIsNone(label.metadata["note_group_id"])
        self.assertIsNone(text.metadata["note_group_id"])

    def test_label_and_text_in_different_zones_do_not_pair(self) -> None:
        label = self._make_block(
            block_id="b1",
            block_order=1,
            source_style="05_ИЦЖТ_Примечание_слово",
            block_subtype="note_label",
            zone=DocumentZone.main_body,
        )
        text = self._make_block(
            block_id="b2",
            block_order=2,
            source_style="05_ИЦЖТ_Примечание_текст после",
            block_subtype="note_text",
            zone=DocumentZone.appendix,
        )

        blocks = [label, text]
        apply_note_grouping(blocks)

        self.assertTrue(label.metadata["is_orphan"])
        self.assertTrue(text.metadata["is_orphan"])

    def test_note_text_metadata_is_preserved(self) -> None:
        label = self._make_block(
            block_id="b1",
            block_order=1,
            source_style="05_ИЦЖТ_Примечание_слово",
            block_subtype="note_label",
        )
        text = self._make_block(
            block_id="b2",
            block_order=2,
            source_style="05_ИЦЖТ_Примечание_текст после",
            block_subtype="note_text",
            metadata={"custom_text_flag": "keep-me"},
        )

        blocks = [label, text]
        apply_note_grouping(blocks)

        self.assertEqual(text.metadata["custom_text_flag"], "keep-me")
        self.assertEqual(text.metadata["existing"], "value")

    def test_apply_note_grouping_is_idempotent_for_existing_marked_blocks(self) -> None:
        label = self._make_block(
            block_id="b1",
            block_order=1,
            source_style="05_ИЦЖТ_Примечание_слово",
            block_subtype="note_label",
            block_type=BlockType.note_label,
            metadata={"note_group_id": "note_group_0042", "is_orphan": False, "note_role": "label"},
        )
        text = self._make_block(
            block_id="b2",
            block_order=2,
            source_style="05_ИЦЖТ_Примечание_текст после",
            block_subtype="note_text",
            block_type=BlockType.note_text,
            metadata={"note_group_id": "note_group_0042", "is_orphan": False, "note_role": "text"},
        )

        blocks = [label, text]
        apply_note_grouping(blocks)
        first = (label.metadata.copy(), text.metadata.copy())

        apply_note_grouping(blocks)
        second = (label.metadata.copy(), text.metadata.copy())

        self.assertEqual(first, second)
        self.assertEqual(label.metadata["note_group_id"], "note_group_0042")
        self.assertEqual(text.metadata["note_group_id"], "note_group_0042")

    def test_count_logical_notes(self) -> None:
        paired_label = self._make_block(
            block_id="b1",
            block_order=1,
            source_style="05_ИЦЖТ_Примечание_слово",
            block_subtype="note_label",
            block_type=BlockType.note_label,
            metadata={"note_group_id": "note_group_0001", "is_orphan": False, "note_role": "label"},
        )
        paired_text = self._make_block(
            block_id="b2",
            block_order=2,
            source_style="05_ИЦЖТ_Примечание_текст после",
            block_subtype="note_text",
            block_type=BlockType.note_text,
            metadata={"note_group_id": "note_group_0001", "is_orphan": False, "note_role": "text"},
        )
        orphan_label = self._make_block(
            block_id="b3",
            block_order=3,
            source_style="05_ИЦЖТ_Примечание_слово",
            block_subtype="note_label",
            block_type=BlockType.note_label,
            metadata={"note_group_id": None, "is_orphan": True, "note_role": "label"},
        )
        orphan_text = self._make_block(
            block_id="b4",
            block_order=4,
            source_style="05_ИЦЖТ_Примечание_текст после",
            block_subtype="note_text",
            block_type=BlockType.note_text,
            metadata={"note_group_id": None, "is_orphan": True, "note_role": "text"},
        )
        legacy_note = self._make_block(
            block_id="b5",
            block_order=5,
            source_style="05_ИЦЖТ_Примечание_слово",
            block_subtype="note_label",
            block_type=BlockType.note_like,
        )

        self.assertEqual(
            _count_logical_notes([paired_label, paired_text, orphan_label, orphan_text, legacy_note]),
            4,
        )


if __name__ == "__main__":
    unittest.main()
