from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from qms_doc_parser.models.parser_models import (
    BlockFlags,
    BlockType,
    DocumentZone,
    HeadingInfo,
    IndentInfo,
    ListInfo,
    ListType,
    ParserBlock,
    SectionContext,
    SourceLocation,
    StyleFlags,
)
from qms_doc_parser.models.registry_models import StyleRegistryConfig


@dataclass
class ClassificationInput:
    block_id: str
    block_order: int
    text: Optional[str]
    style_name: Optional[str]
    current_zone: Optional[str] = None
    paragraph_index: Optional[int] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    left_indent: Optional[int] = None
    first_line_indent: Optional[int] = None


class StyleClassifier:
    def __init__(self, registry: StyleRegistryConfig):
        self.registry = registry

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace("\xa0", " ").replace("\t", " ")
        text = re.sub(r"[ ]{2,}", " ", text)
        return text.strip()

    def classify(self, inp: ClassificationInput) -> ParserBlock:
        raw_text = inp.text or ""
        normalized_text = self.normalize_text(raw_text)
        style_name = (inp.style_name or "").strip()

        flags = BlockFlags()
        style_flags = StyleFlags(bold=inp.bold, italic=inp.italic, underline=inp.underline)
        indent = IndentInfo(left=inp.left_indent, first_line=inp.first_line_indent)

        if not normalized_text:
            flags.is_empty = True
            return ParserBlock(
                block_id=inp.block_id,
                block_order=inp.block_order,
                document_zone=DocumentZone.unknown_zone,
                block_type=BlockType.empty,
                raw_text=raw_text,
                normalized_text=normalized_text,
                source_style=style_name or None,
                style_flags=style_flags,
                indent=indent,
                section_context=SectionContext(),
                source_location=SourceLocation(paragraph_index=inp.paragraph_index),
                flags=flags,
            )

        rule = self.registry.style_registry.get(style_name)
        if rule:
            zone = DocumentZone(rule.default_zone) if rule.default_zone in DocumentZone._value2member_map_ else DocumentZone.unknown_zone
            block_type = BlockType(rule.block_type) if rule.block_type in BlockType._value2member_map_ else BlockType.unknown

            heading_info = None
            list_info = None

            if block_type in {BlockType.heading, BlockType.appendix_heading}:
                heading_info = HeadingInfo(
                    heading_level=rule.heading_level,
                    heading_number=self._extract_heading_number(normalized_text),
                    heading_title=self._extract_heading_title(normalized_text),
                    detection_method="style_registry",
                    confidence=0.99,
                )

            if block_type == BlockType.list_item:
                list_info = ListInfo(
                    list_type=self._safe_list_type(rule.list_type),
                    list_marker=self._extract_list_marker(normalized_text),
                    list_level=rule.list_level,
                    detection_method="style_registry",
                )

            for flag in rule.flags:
                if hasattr(flags, flag):
                    setattr(flags, flag, True)

            return ParserBlock(
                block_id=inp.block_id,
                block_order=inp.block_order,
                document_zone=zone,
                block_type=block_type,
                block_subtype=rule.block_subtype,
                raw_text=raw_text,
                normalized_text=normalized_text,
                source_style=style_name or None,
                style_flags=style_flags,
                indent=indent,
                heading_info=heading_info,
                list_info=list_info,
                section_context=SectionContext(),
                source_location=SourceLocation(paragraph_index=inp.paragraph_index),
                flags=flags,
            )

        # fallback
        flags.needs_review = True
        flags.is_suspicious = True

        if re.match(r"^\s*(\d+(\.\d+){0,5})\s+.+$", normalized_text):
            return ParserBlock(
                block_id=inp.block_id,
                block_order=inp.block_order,
                document_zone=DocumentZone.main_body,
                block_type=BlockType.heading,
                block_subtype="numbered_heading_fallback",
                raw_text=raw_text,
                normalized_text=normalized_text,
                source_style=style_name or None,
                style_flags=style_flags,
                indent=indent,
                heading_info=HeadingInfo(
                    heading_level=self._infer_heading_level(normalized_text),
                    heading_number=self._extract_heading_number(normalized_text),
                    heading_title=self._extract_heading_title(normalized_text),
                    detection_method="text_fallback",
                    confidence=0.75,
                ),
                section_context=SectionContext(),
                source_location=SourceLocation(paragraph_index=inp.paragraph_index),
                flags=flags,
            )

        return ParserBlock(
            block_id=inp.block_id,
            block_order=inp.block_order,
            document_zone=DocumentZone.main_body,
            block_type=BlockType.paragraph,
            block_subtype="plain_paragraph_fallback",
            raw_text=raw_text,
            normalized_text=normalized_text,
            source_style=style_name or None,
            style_flags=style_flags,
            indent=indent,
            section_context=SectionContext(),
            source_location=SourceLocation(paragraph_index=inp.paragraph_index),
            flags=flags,
        )

    def _extract_heading_number(self, text: str) -> Optional[str]:
        m = re.match(r"^\s*(\d+(?:\.\d+){0,5})\b", text)
        return m.group(1) if m else None

    def _extract_heading_title(self, text: str) -> Optional[str]:
        m = re.match(r"^\s*\d+(?:\.\d+){0,5}\s+(.+)$", text)
        return m.group(1).strip() if m else text.strip()

    def _infer_heading_level(self, text: str) -> Optional[int]:
        number = self._extract_heading_number(text)
        return number.count(".") + 1 if number else None

    def _extract_list_marker(self, text: str) -> Optional[str]:
        for pattern in [r"^\s*([A-Za-zА-Яа-я]\))\s+", r"^\s*(\d+[\.\)])\s+", r"^\s*([-•–])\s+"]:
            m = re.match(pattern, text)
            if m:
                return m.group(1)
        return None

    def _safe_list_type(self, value: Optional[str]) -> Optional[ListType]:
        if not value:
            return None
        mapping = {
            "numbered": ListType.numbered,
            "bulleted": ListType.bulleted,
            "bulleted_dash": ListType.bulleted,
            "lettered": ListType.lettered,
            "unknown": ListType.unknown,
        }
        return mapping.get(value, ListType.unknown)