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
                document_zone=self._determine_empty_zone(inp.current_zone),
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
            zone = self._safe_document_zone(rule.default_zone)
            block_type = self._safe_block_type(rule.block_type)

            if block_type in {BlockType.paragraph, BlockType.heading}:
                inferred_type = self._infer_heading_block_type(style_name, normalized_text, current_zone=inp.current_zone)
                if inferred_type is not None:
                    block_type = inferred_type
                    zone = self._determine_zone(
                        block_type=block_type,
                        style_name=style_name,
                        normalized_text=normalized_text,
                        current_zone=inp.current_zone,
                        default_zone=zone,
                    )

            heading_info = None
            list_info = None

            if block_type in {BlockType.heading, BlockType.appendix_heading}:
                heading_info = HeadingInfo(
                    heading_level=self._resolve_heading_level(block_type, rule.heading_level, style_name, normalized_text),
                    heading_number=self._extract_heading_number(normalized_text, block_type=block_type),
                    heading_title=self._extract_heading_title(normalized_text, block_type=block_type),
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

            zone = self._determine_zone(
                block_type=block_type,
                style_name=style_name,
                normalized_text=normalized_text,
                current_zone=inp.current_zone,
                default_zone=zone,
            )

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

        fallback_block_type = self._infer_heading_block_type(style_name, normalized_text, current_zone=inp.current_zone)
        if fallback_block_type is None and re.match(r"^\s*(\d+(\.\d+){0,5})\s+.+$", normalized_text):
            fallback_block_type = BlockType.heading

        if fallback_block_type is not None:
            flags.needs_review = True
            flags.is_suspicious = True
            return ParserBlock(
                block_id=inp.block_id,
                block_order=inp.block_order,
                document_zone=self._determine_zone(
                    block_type=fallback_block_type,
                    style_name=style_name,
                    normalized_text=normalized_text,
                    current_zone=inp.current_zone,
                    default_zone=DocumentZone.main_body,
                ),
                block_type=fallback_block_type,
                block_subtype=(
                    "appendix_heading_fallback"
                    if fallback_block_type == BlockType.appendix_heading
                    else "style_heading_fallback"
                    if self._style_implies_heading(style_name)
                    else "numbered_heading_fallback"
                ),
                raw_text=raw_text,
                normalized_text=normalized_text,
                source_style=style_name or None,
                style_flags=style_flags,
                indent=indent,
                heading_info=HeadingInfo(
                    heading_level=self._resolve_heading_level(fallback_block_type, None, style_name, normalized_text),
                    heading_number=self._extract_heading_number(normalized_text, block_type=fallback_block_type),
                    heading_title=self._extract_heading_title(normalized_text, block_type=fallback_block_type),
                    detection_method="text_fallback" if not self._style_implies_heading(style_name) else "style_fallback",
                    confidence=0.75,
                ),
                section_context=SectionContext(),
                source_location=SourceLocation(paragraph_index=inp.paragraph_index),
                flags=flags,
            )

        flags.needs_review = True
        flags.is_suspicious = True
        return ParserBlock(
            block_id=inp.block_id,
            block_order=inp.block_order,
            document_zone=self._determine_zone(
                block_type=BlockType.paragraph,
                style_name=style_name,
                normalized_text=normalized_text,
                current_zone=inp.current_zone,
                default_zone=DocumentZone.main_body,
            ),
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

    def _safe_document_zone(self, value: str) -> DocumentZone:
        if value in DocumentZone._value2member_map_:
            return DocumentZone(value)
        return DocumentZone.unknown_zone

    def _safe_block_type(self, value: str) -> BlockType:
        if value in BlockType._value2member_map_:
            return BlockType(value)
        return BlockType.unknown

    def _infer_heading_block_type(self, style_name: str, normalized_text: str, current_zone: Optional[str]) -> Optional[BlockType]:
        in_appendix_context = current_zone == DocumentZone.appendix.value

        if self._style_implies_appendix_heading(style_name):
            return BlockType.appendix_heading
        if self._looks_like_appendix_root(normalized_text):
            return BlockType.appendix_heading
        if in_appendix_context and self._looks_like_appendix_subheading(normalized_text):
            return BlockType.appendix_heading
        if in_appendix_context and self._style_implies_heading(style_name) and self._allows_appendix_heading_in_context(normalized_text):
            return BlockType.appendix_heading
        if self._style_implies_heading(style_name) and self._allows_style_heading_fallback(normalized_text):
            return BlockType.heading
        return None

    def _determine_empty_zone(self, current_zone: Optional[str]) -> DocumentZone:
        if current_zone in {
            DocumentZone.title_page.value,
            DocumentZone.control_sheet.value,
            DocumentZone.toc.value,
        }:
            return DocumentZone(current_zone)
        return DocumentZone.unknown_zone

    def _determine_zone(
        self,
        *,
        block_type: BlockType,
        style_name: str,
        normalized_text: str,
        current_zone: Optional[str],
        default_zone: DocumentZone,
    ) -> DocumentZone:
        current = self._safe_document_zone(current_zone) if current_zone else None

        if block_type == BlockType.appendix_heading or self._text_implies_appendix_heading(normalized_text):
            return DocumentZone.appendix

        if self._is_control_sheet_anchor(style_name, normalized_text):
            return DocumentZone.control_sheet

        if self._is_toc_anchor(style_name, normalized_text) or block_type == BlockType.toc_item:
            return DocumentZone.toc

        if self._is_bibliography_anchor(style_name, normalized_text) or block_type == BlockType.bibliography_item:
            return DocumentZone.bibliography

        if self._is_title_page_style(style_name) and current not in {DocumentZone.control_sheet, DocumentZone.toc, DocumentZone.main_body, DocumentZone.appendix, DocumentZone.bibliography}:
            return DocumentZone.title_page

        if block_type == BlockType.heading:
            return DocumentZone.main_body

        if current == DocumentZone.appendix:
            return DocumentZone.appendix

        if current == DocumentZone.bibliography:
            if block_type in {BlockType.heading, BlockType.appendix_heading}:
                return DocumentZone.appendix if block_type == BlockType.appendix_heading else DocumentZone.main_body
            return DocumentZone.bibliography

        if current == DocumentZone.toc:
            if block_type == BlockType.heading and not self._is_toc_anchor(style_name, normalized_text):
                return DocumentZone.main_body
            if block_type == BlockType.toc_item or self._is_toc_anchor(style_name, normalized_text):
                return DocumentZone.toc

        if current == DocumentZone.control_sheet:
            if block_type in {BlockType.heading, BlockType.appendix_heading}:
                return DocumentZone.appendix if block_type == BlockType.appendix_heading else DocumentZone.main_body
            return DocumentZone.control_sheet

        if current == DocumentZone.title_page:
            if block_type in {BlockType.title_meta}:
                return DocumentZone.title_page
            if block_type in {BlockType.heading, BlockType.appendix_heading}:
                return DocumentZone.appendix if block_type == BlockType.appendix_heading else DocumentZone.main_body
            if default_zone == DocumentZone.main_body and not style_name:
                return DocumentZone.title_page

        if default_zone != DocumentZone.unknown_zone:
            return default_zone

        if current is not None:
            return current

        return DocumentZone.main_body

    def _extract_heading_number(self, text: str, block_type: BlockType = BlockType.heading) -> Optional[str]:
        if block_type == BlockType.appendix_heading:
            appendix_match = re.match(r"^\s*Приложение\s+([А-ЯA-Z])\b", text, flags=re.IGNORECASE)
            if appendix_match:
                return appendix_match.group(1).upper()
            appendix_number_match = re.match(r"^\s*([А-ЯA-Z](?:\.\d+){0,5})\b", text)
            if appendix_number_match:
                return appendix_number_match.group(1)

        m = re.match(r"^\s*(\d+(?:\.\d+){0,5})\b", text)
        return m.group(1) if m else None

    def _extract_heading_title(self, text: str, block_type: BlockType = BlockType.heading) -> Optional[str]:
        if block_type == BlockType.appendix_heading:
            appendix_root_match = re.match(r"^\s*Приложение\s+[А-ЯA-Z]\s*(.+)?$", text, flags=re.IGNORECASE)
            if appendix_root_match:
                appendix_title = (appendix_root_match.group(1) or "").strip(" .:-")
                return appendix_title or text.strip()
            appendix_section_match = re.match(r"^\s*[А-ЯA-Z](?:\.\d+){0,5}\s+(.+)$", text)
            if appendix_section_match:
                return appendix_section_match.group(1).strip()

        m = re.match(r"^\s*\d+(?:\.\d+){0,5}\s+(.+)$", text)
        return m.group(1).strip() if m else text.strip()

    def _infer_heading_level(self, text: str, block_type: BlockType = BlockType.heading) -> Optional[int]:
        number = self._extract_heading_number(text, block_type=block_type)
        if not number:
            return None
        return number.count(".") + 1

    def _resolve_heading_level(
        self,
        block_type: BlockType,
        registry_level: Optional[int],
        style_name: str,
        normalized_text: str,
    ) -> Optional[int]:
        inferred_level = self._infer_heading_level(normalized_text, block_type=block_type)
        style_level = self._extract_heading_level_from_style(style_name)

        if block_type == BlockType.appendix_heading:
            if inferred_level is not None:
                return inferred_level
            if re.match(r"^\s*Приложение\s+[А-ЯA-Z]\b", normalized_text, flags=re.IGNORECASE):
                return 1
            if registry_level is not None:
                return registry_level if registry_level > 1 else 2
            if style_level is not None:
                return max(style_level, 2)
            return 2

        if registry_level is not None:
            return registry_level
        if style_level is not None:
            return style_level
        if inferred_level is not None:
            return inferred_level

        return 1 if block_type in {BlockType.heading, BlockType.appendix_heading} else None

    def _extract_heading_level_from_style(self, style_name: str) -> Optional[int]:
        match = re.search(r"(?:^|\s)(?:Heading|Заголовок)\s*(\d+)\b", style_name, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _style_implies_heading(self, style_name: str) -> bool:
        if not style_name:
            return False
        normalized_style = style_name.casefold()
        if "таблиц" in normalized_style or "рисунок" in normalized_style or "оглавление" in normalized_style:
            return False
        return "heading" in normalized_style or "заголовок" in normalized_style

    def _style_implies_appendix_heading(self, style_name: str) -> bool:
        if not style_name:
            return False
        normalized_style = style_name.casefold()
        return "прил" in normalized_style and self._style_implies_heading(style_name)

    def _text_implies_appendix_heading(self, text: str) -> bool:
        return self._looks_like_appendix_root(text) or self._looks_like_appendix_subheading(text)

    def _looks_like_appendix_root(self, text: str) -> bool:
        return bool(
            re.match(
                r"^\s*Приложение\s+[А-ЯA-Z]\b(?:\s*\([^)]*\))?(?:\s*[—:-]\s*.+|\s+.+)?$",
                text,
                flags=re.IGNORECASE,
            )
        )

    def _looks_like_appendix_subheading(self, text: str) -> bool:
        return bool(re.match(r"^\s*[А-ЯA-Z](?:\.\d+){1,5}\s+.+$", text))

    def _allows_appendix_heading_in_context(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        if self._looks_like_appendix_subheading(stripped):
            return True
        if stripped.startswith("(") and len(self._split_words(stripped)) <= 8 and not self._has_terminal_sentence_punctuation(stripped):
            return True
        return self._allows_style_heading_fallback(stripped)

    def _allows_style_heading_fallback(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        if self._looks_like_appendix_root(stripped) or self._looks_like_appendix_subheading(stripped):
            return True
        if re.match(r"^\s*(\d+(?:\.\d+){0,5})\s+.+$", stripped):
            return True
        if self._has_terminal_sentence_punctuation(stripped):
            return False
        if any(mark in stripped for mark in [",", ";"]):
            return False
        word_count = len(self._split_words(stripped))
        if word_count == 0 or word_count > 8:
            return False
        if len(stripped) > 80:
            return False
        return True

    def _has_terminal_sentence_punctuation(self, text: str) -> bool:
        return text.rstrip().endswith((".", "!", "?", ";", ":"))

    def _split_words(self, text: str) -> list[str]:
        return re.findall(r"[\wА-Яа-яA-Za-z-]+", text, flags=re.UNICODE)

    def _is_title_page_style(self, style_name: str) -> bool:
        if not style_name:
            return False
        normalized_style = style_name.casefold()
        return "титуль" in normalized_style or "title" in normalized_style

    def _is_control_sheet_anchor(self, style_name: str, normalized_text: str) -> bool:
        if normalized_text.casefold() == "контрольный лист":
            return True
        normalized_style = style_name.casefold()
        return "структурный" in normalized_style and "вне содержания" in normalized_style and "контрольный лист" in normalized_text.casefold()

    def _is_toc_anchor(self, style_name: str, normalized_text: str) -> bool:
        if normalized_text.casefold() == "содержание":
            return True
        normalized_style = style_name.casefold()
        return "оглавление" in normalized_style or "содержание" in normalized_style

    def _is_bibliography_anchor(self, style_name: str, normalized_text: str) -> bool:
        if normalized_text.casefold() == "библиография":
            return True
        normalized_style = style_name.casefold()
        return "список источников" in normalized_style or "библиограф" in normalized_style

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
