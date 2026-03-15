from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from qms_doc_parser.models.parser_models import (
    BlockType,
    ParserBlock,
    SectionContext,
    DocumentZone,
)


@dataclass
class SectionNode:
    section_id: str
    section_title: str
    section_level: int
    zone: DocumentZone


@dataclass
class SectionTrackerState:
    main_stack: List[SectionNode] = field(default_factory=list)
    appendix_stack: List[SectionNode] = field(default_factory=list)


class SectionTracker:
    """
    Tracks current section hierarchy for:
    - main body headings
    - appendix headings

    Rules:
    - main_body headings update main_stack
    - appendix headings update appendix_stack
    - non-heading blocks inherit current stack by zone
    - toc/title/template zones do not affect main/appendix stacks
    """

    def __init__(self) -> None:
        self.state = SectionTrackerState()

    def apply(self, block: ParserBlock) -> ParserBlock:
        if block.block_type == BlockType.heading and block.document_zone == DocumentZone.main_body:
            self._update_main_stack(block)
            block.section_context = self._build_context_from_stack(self.state.main_stack)
            return block

        if block.block_type == BlockType.appendix_heading and block.document_zone == DocumentZone.appendix:
            self._update_appendix_stack(block)
            block.section_context = self._build_context_from_stack(self.state.appendix_stack)
            return block

        if block.document_zone == DocumentZone.main_body:
            block.section_context = self._build_context_from_stack(self.state.main_stack)
            return block

        if block.document_zone == DocumentZone.appendix:
            block.section_context = self._build_context_from_stack(self.state.appendix_stack)
            return block

        # For other zones, keep empty context
        block.section_context = SectionContext()
        return block

    def _update_main_stack(self, block: ParserBlock) -> None:
        heading_level = self._extract_heading_level(block)
        if heading_level is None:
            heading_level = 1

        section_id = self._extract_main_section_id(block)
        section_title = self._extract_section_title(block)

        self._trim_stack(self.state.main_stack, heading_level)
        self.state.main_stack.append(
            SectionNode(
                section_id=section_id,
                section_title=section_title,
                section_level=heading_level,
                zone=DocumentZone.main_body,
            )
        )

    def _update_appendix_stack(self, block: ParserBlock) -> None:
        heading_level = self._extract_heading_level(block)
        if heading_level is None:
            heading_level = 1

        section_id = self._extract_appendix_section_id(block)
        section_title = self._extract_section_title(block)

        self._trim_stack(self.state.appendix_stack, heading_level)
        self.state.appendix_stack.append(
            SectionNode(
                section_id=section_id,
                section_title=section_title,
                section_level=heading_level,
                zone=DocumentZone.appendix,
            )
        )

    def _trim_stack(self, stack: List[SectionNode], new_level: int) -> None:
        while stack and stack[-1].section_level >= new_level:
            stack.pop()

    def _build_context_from_stack(self, stack: List[SectionNode]) -> SectionContext:
        if not stack:
            return SectionContext()

        current = stack[-1]
        parent_section_id = stack[-2].section_id if len(stack) > 1 else None

        return SectionContext(
            section_id=current.section_id,
            section_title=current.section_title,
            section_level=current.section_level,
            section_path=[node.section_id for node in stack],
            parent_section_id=parent_section_id,
        )

    def _extract_heading_level(self, block: ParserBlock) -> Optional[int]:
        if block.heading_info and block.heading_info.heading_level:
            return block.heading_info.heading_level
        return None

    def _extract_section_title(self, block: ParserBlock) -> str:
        if block.heading_info and block.heading_info.heading_title:
            return block.heading_info.heading_title.strip()
        if block.normalized_text:
            return block.normalized_text.strip()
        return ""

    def _extract_main_section_id(self, block: ParserBlock) -> str:
        if block.heading_info and block.heading_info.heading_number:
            return block.heading_info.heading_number.strip()

        text = block.normalized_text or ""
        m = re.match(r"^\s*(\d+(?:\.\d+){0,5})\b", text)
        if m:
            return m.group(1)

        # Fallback if someone broke numbering but kept heading style
        return f"UNNUMBERED_{block.block_order}"

    def _extract_appendix_section_id(self, block: ParserBlock) -> str:
        """
        Expected examples:
        - 'Приложение А'
        - 'А.1 Название'
        - 'А.1.1 Название'
        """
        text = (block.normalized_text or "").strip()

        # Example: "Приложение А"
        m = re.match(r"^\s*Приложение\s+([А-ЯA-Z])\b", text)
        if m:
            return m.group(1)

        # Example: "А.1 ..." or "A.1 ..."
        m = re.match(r"^\s*([А-ЯA-Z](?:\.\d+){0,5})\b", text)
        if m:
            return m.group(1)

        # If heading_info already has something useful, use it
        if block.heading_info and block.heading_info.heading_number:
            return block.heading_info.heading_number.strip()

        return f"APP_UNNUMBERED_{block.block_order}"