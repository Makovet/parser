from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


STYLE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "0_ИЦЖТ_Текст": {"block_type": "paragraph"},
    "0_ИЦЖТ_Текст_без отступа": {"block_type": "paragraph", "block_subtype": "definition_like"},
    "0_ИЦЖТ_Для удаления": {
        "block_type": "template_instruction",
        "flags": {"is_template_instruction": True, "is_deletable_template_content": True},
    },
    "0_ИЦЖТ_Титульный_Заголовки": {"block_type": "title_meta", "document_zone": "title_page"},
    "0_ИЦЖТ_Заголовок_Структурный (вне содержания)": {"block_type": "heading"},
    "0_ИЦЖТ_Заголовок_Структурный": {"block_type": "heading"},
    "Оглавление 1": {"block_type": "toc_item", "toc_level": 1},
    "Оглавление 2": {"block_type": "toc_item", "toc_level": 2},
    "Оглавление 3": {"block_type": "toc_item", "toc_level": 3},
    "Заголовок 1": {"block_type": "heading", "heading_level": 1},
    "Заголовок 2": {"block_type": "heading", "heading_level": 2},
    "Заголовок 3": {"block_type": "heading", "heading_level": 3},
    "Заголовок 4": {"block_type": "heading", "heading_level": 4},
    "Заголовок 5": {"block_type": "heading", "heading_level": 5},
    "Заголовок 6": {"block_type": "heading", "heading_level": 6},
    "Заголовок 7;Прил. A": {"block_type": "appendix_heading", "heading_level": 1},
    "Заголовок 8;Прил. А.1": {"block_type": "appendix_heading", "heading_level": 2},
    "Заголовок 9;Прил A.1.1": {"block_type": "appendix_heading", "heading_level": 3},
    "0_ИЦЖТ_Список источников": {"block_type": "bibliography_item"},
    "01_ИЦЖТ_слово_ТАБЛИЦА": {"block_type": "table_label"},
    "01_ИЦЖТ_таблица_названия": {"block_type": "table_caption"},
    "03_ИЦЖТ_Перечисление_1 ур. = -": {"block_type": "list_item", "list_type": "bulleted_dash", "list_level": 1},
    "03_ИЦЖТ_Перечисление_1 ур. = абв": {"block_type": "list_item", "list_type": "lettered", "list_level": 1},
    "03_ИЦЖТ_Перечисление_2 ур. = 1)": {"block_type": "list_item", "list_type": "numbered", "list_level": 2},
    "03_ИЦЖТ_Перечисление_3 ур. = -": {"block_type": "list_item", "list_type": "bulleted_dash", "list_level": 3},
    "02_ИЦЖТ_рисунок": {"block_type": "figure"},
    "02_ИЦЖТ_Рисунок_название": {"block_type": "figure_caption"},
    "02_ИЦЖТ_Рисунок_подрисуночный текст": {"block_type": "figure_explanation"},
    "04_ИЦЖТ_формула": {"block_type": "formula"},
    "04_ИЦЖТ_формула_поясн.1": {"block_type": "formula_explanation", "block_subtype": "where_start"},
    "04_ИЦЖТ_формула_поясн.2": {"block_type": "formula_explanation", "block_subtype": "where_continuation"},
    "04_ИЦЖТ_формула_нумерация": {"block_type": "formula_number"},
    "05_ИЦЖТ_Примечание_слово": {"block_type": "note_like", "block_subtype": "note_label"},
    "05_ИЦЖТ_Примечание_текст после": {"block_type": "note_like", "block_subtype": "note_text"},
    "10_ИЦЖТ_Код в тексте": {"block_type": "code_inline"},
    "10_ИЦЖТ_Код выключной": {"block_type": "code_block"},
    "10_ИЦЖТ_Код ключевые слова": {"block_type": "code_inline", "block_subtype": "code_keyword"},
    "10_ИЦЖТ_Код комментарии": {"block_type": "code_inline", "block_subtype": "code_comment"},
}

DOCUMENT_ZONES = {
    "title_page",
    "control_sheet",
    "toc",
    "main_body",
    "appendix",
    "bibliography",
    "template_instruction",
    "a3_template_section",
    "footer_or_header",
    "unknown_zone",
}

TEMPLATE_HINTS = (
    "внимание",
    "удалить при разработке",
    "выберите один из вариантов",
    "лишнее удалить",
    "добавить ссылку",
    "размещен только для образца",
    "для удаления",
)


@dataclass
class SectionContext:
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    section_level: Optional[int] = None
    section_path: List[str] = field(default_factory=list)
    parent_section_id: Optional[str] = None


@dataclass
class ParsedBlock:
    block_id: str
    block_order: int
    document_zone: str
    block_type: str
    block_subtype: Optional[str]
    raw_text: str
    normalized_text: str
    source_style: Optional[str]
    style_flags: Dict[str, bool]
    indent: Dict[str, int]
    heading_info: Optional[Dict[str, Any]] = None
    list_info: Optional[Dict[str, Any]] = None
    table_info: Optional[Dict[str, Any]] = None
    figure_info: Optional[Dict[str, Any]] = None
    formula_info: Optional[Dict[str, Any]] = None
    note_info: Optional[Dict[str, Any]] = None
    section_context: Dict[str, Any] = field(default_factory=lambda: asdict(SectionContext()))
    source_location: Dict[str, Any] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)


class ParserLayerV03:
    parser_version = "0.3.0"
    template_id = "ADM-TEM-011_B"

    def __init__(self) -> None:
        self._section_stack: List[Tuple[str, str, int]] = []
        self._appendix_stack: List[Tuple[str, str, int]] = []

    def parse(self, file_name: str, blocks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        parsed_blocks: List[Dict[str, Any]] = []
        style_registry_used = set()

        for idx, raw_block in enumerate(blocks, start=1):
            parsed = self._parse_block(raw_block, idx)
            parsed_blocks.append(asdict(parsed))
            if parsed.source_style and parsed.source_style in STYLE_REGISTRY:
                style_registry_used.add(parsed.source_style)

        composite = self._build_composites(parsed_blocks)
        return {
            "document_id": self._generate_document_id(file_name),
            "template_id": self.template_id,
            "source": {
                "file_name": file_name,
                "file_type": "docx",
                "file_hash": self._pseudo_hash(file_name),
                "parser_version": self.parser_version,
                "processed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "language": "ru",
            },
            "document_metadata": {
                "title": None,
                "document_code": None,
                "document_type": None,
                "revision": None,
                "confidentiality_level": None,
            },
            "structure_summary": self._summary(parsed_blocks, composite),
            "style_registry_used": sorted(style_registry_used),
            "blocks": parsed_blocks,
            "composite_objects": composite,
        }

    def _parse_block(self, raw: Dict[str, Any], order: int) -> ParsedBlock:
        source_style = raw.get("source_style")
        raw_text = raw.get("raw_text", "")
        normalized_text = self._normalize_text(raw_text)
        style_data = STYLE_REGISTRY.get(source_style or "", {})

        block_type = style_data.get("block_type") or self._fallback_block_type(raw_text)
        block_subtype = style_data.get("block_subtype")
        zone = style_data.get("document_zone") or self._detect_zone(raw_text, block_type)

        flags = self._default_flags()
        if not normalized_text:
            flags["is_empty"] = True
            block_type = "empty"
        if source_style not in STYLE_REGISTRY:
            flags["needs_review"] = True
            flags["is_suspicious"] = True
        if self._is_template_text(normalized_text) or block_type == "template_instruction":
            flags["is_template_instruction"] = True
            flags["is_deletable_template_content"] = True
            zone = "template_instruction"
        if zone == "footer_or_header":
            flags["is_header_footer_artifact"] = True

        if zone in {"title_page", "control_sheet", "toc"}:
            flags["is_front_matter"] = True
        if block_type == "toc_item":
            flags["is_generated_toc_entry"] = True

        heading_info = None
        section_context = asdict(SectionContext())
        if block_type in {"heading", "appendix_heading"}:
            level = style_data.get("heading_level", 1)
            section_id = self._extract_section_id(normalized_text)
            heading_info = {"level": level, "section_id": section_id, "detection_method": "style_registry"}
            section_context = self._update_section_context(block_type, level, section_id, normalized_text)
        elif self._section_stack and zone in {"main_body", "appendix", "bibliography"}:
            section_context = self._current_section_context(zone)

        list_info = None
        if block_type == "list_item":
            list_info = {
                "list_type": style_data.get("list_type", "unknown"),
                "list_level": style_data.get("list_level", 1),
                "list_marker": raw.get("list_marker"),
                "list_parent_block_id": None,
                "list_parent_marker": None,
                "list_path": [],
                "detection_method": "style_registry" if source_style in STYLE_REGISTRY else "fallback",
            }

        return ParsedBlock(
            block_id=f"b{order:06d}",
            block_order=order,
            document_zone=zone if zone in DOCUMENT_ZONES else "unknown_zone",
            block_type=block_type,
            block_subtype=block_subtype,
            raw_text=raw_text,
            normalized_text=normalized_text,
            source_style=source_style,
            style_flags=raw.get("style_flags", {"bold": False, "italic": False, "underline": False}),
            indent=raw.get("indent", {"left": 0, "first_line": 0}),
            heading_info=heading_info,
            list_info=list_info,
            source_location=raw.get(
                "source_location",
                {
                    "paragraph_index": raw.get("paragraph_index"),
                    "table_index": raw.get("table_index"),
                    "row_index": raw.get("row_index"),
                    "cell_index": raw.get("cell_index"),
                    "figure_index": raw.get("figure_index"),
                    "header_footer": raw.get("header_footer"),
                },
            ),
            flags=flags | style_data.get("flags", {}),
            section_context=section_context,
        )

    def _build_composites(self, blocks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "tables": self._collect_tables(blocks),
            "figures": self._collect_figures(blocks),
            "formulas": self._collect_formulas(blocks),
            "notes": self._collect_notes(blocks),
        }

    def _collect_tables(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        table_counter = 1
        for i, block in enumerate(blocks):
            if block["block_type"] != "table":
                continue
            label = blocks[i - 2] if i > 1 and blocks[i - 2]["block_type"] == "table_label" else None
            caption = blocks[i - 1] if i > 0 and blocks[i - 1]["block_type"] == "table_caption" else None
            result.append(
                {
                    "table_id": f"t{table_counter:04d}",
                    "table_block_id": block["block_id"],
                    "label_block_id": label["block_id"] if label else None,
                    "caption_block_id": caption["block_id"] if caption else None,
                    "post_table_note_block_ids": [],
                    "table_number": self._extract_number(caption["normalized_text"]) if caption else None,
                    "table_title": caption["normalized_text"] if caption else None,
                    "cells_raw": [],
                    "cells_normalized": [],
                    "section_context": block["section_context"],
                }
            )
            table_counter += 1
        return result

    def _collect_figures(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        counter = 1
        for i, block in enumerate(blocks):
            if block["block_type"] != "figure":
                continue
            caption = blocks[i + 1] if i + 1 < len(blocks) and blocks[i + 1]["block_type"] == "figure_caption" else None
            exp_ids: List[str] = []
            j = i + 1
            while j < len(blocks) and blocks[j]["block_type"] in {"figure_caption", "figure_explanation"}:
                if blocks[j]["block_type"] == "figure_explanation":
                    exp_ids.append(blocks[j]["block_id"])
                j += 1
            if not caption:
                block["flags"]["needs_review"] = True
            result.append(
                {
                    "figure_id": f"f{counter:04d}",
                    "figure_block_id": block["block_id"],
                    "caption_block_id": caption["block_id"] if caption else None,
                    "explanation_block_ids": exp_ids,
                    "figure_number": self._extract_number(caption["normalized_text"]) if caption else None,
                    "figure_title": caption["normalized_text"] if caption else None,
                    "section_context": block["section_context"],
                }
            )
            counter += 1
        return result

    def _collect_formulas(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        counter = 1
        for i, block in enumerate(blocks):
            if block["block_type"] != "formula":
                continue
            number = blocks[i + 1] if i + 1 < len(blocks) and blocks[i + 1]["block_type"] == "formula_number" else None
            exp_ids: List[str] = []
            j = i + 1
            while j < len(blocks) and blocks[j]["block_type"] in {"formula_number", "formula_explanation"}:
                if blocks[j]["block_type"] == "formula_explanation":
                    exp_ids.append(blocks[j]["block_id"])
                j += 1
            if not number:
                block["flags"]["needs_review"] = True
            result.append(
                {
                    "formula_id": f"fm{counter:04d}",
                    "formula_block_id": block["block_id"],
                    "number_block_id": number["block_id"] if number else None,
                    "explanation_block_ids": exp_ids,
                    "formula_number": number["normalized_text"] if number else None,
                    "section_context": block["section_context"],
                }
            )
            counter += 1
        return result

    def _collect_notes(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        counter = 1
        for i, block in enumerate(blocks):
            if block["block_type"] != "note_like" or block.get("block_subtype") != "note_label":
                continue
            text = blocks[i + 1] if i + 1 < len(blocks) and blocks[i + 1].get("block_subtype") == "note_text" else None
            if not text:
                block["flags"]["needs_review"] = True
            full_text = block["normalized_text"] if not text else f"{block['normalized_text']} — {text['normalized_text']}"
            result.append(
                {
                    "note_id": f"n{counter:04d}",
                    "label_block_id": block["block_id"],
                    "text_block_id": text["block_id"] if text else None,
                    "note_type": "note",
                    "full_text": full_text,
                    "section_context": block["section_context"],
                }
            )
            counter += 1
        return result

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = (text or "").replace("\xa0", " ").replace("\t", " ")
        text = re.sub(r"[ ]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _detect_zone(self, text: str, block_type: str) -> str:
        lowered = text.lower()
        if block_type == "toc_item" or "содержание" in lowered:
            return "toc"
        if "контрольный лист" in lowered:
            return "control_sheet"
        if "библиография" in lowered or block_type == "bibliography_item":
            return "bibliography"
        if block_type == "appendix_heading" or re.match(r"^приложение\s+[а-яa-z]", lowered):
            return "appendix"
        if any(h in lowered for h in ("перед использованием копии", "колонтитул")):
            return "footer_or_header"
        return "main_body"

    def _fallback_block_type(self, text: str) -> str:
        t = self._normalize_text(text).lower()
        if not t:
            return "empty"
        if self._is_template_text(t):
            return "template_instruction"
        return "unknown"

    @staticmethod
    def _default_flags() -> Dict[str, bool]:
        return {
            "is_empty": False,
            "is_suspicious": False,
            "needs_review": False,
            "is_template_instruction": False,
            "is_template_placeholder": False,
            "is_example_content": False,
            "is_front_matter": False,
            "is_generated_toc_entry": False,
            "is_header_footer_artifact": False,
            "is_deletable_template_content": False,
        }

    @staticmethod
    def _is_template_text(text: str) -> bool:
        lowered = text.lower()
        return any(hint in lowered for hint in TEMPLATE_HINTS)

    @staticmethod
    def _extract_number(text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        match = re.search(r"(\d+(?:\.\d+)*)", text)
        return match.group(1) if match else None

    @staticmethod
    def _extract_section_id(text: str) -> Optional[str]:
        patterns = [r"^(\d+(?:\.\d+)*)", r"^(?:приложение\s+)?([A-ZА-Я](?:\.\d+)*)"]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _update_section_context(self, block_type: str, level: int, section_id: Optional[str], title: str) -> Dict[str, Any]:
        sid = section_id or title
        stack = self._appendix_stack if block_type == "appendix_heading" else self._section_stack
        while stack and stack[-1][2] >= level:
            stack.pop()
        stack.append((sid, title, level))
        path = [x[0] for x in stack]
        return {
            "section_id": sid,
            "section_title": title,
            "section_level": level,
            "section_path": path,
            "parent_section_id": path[-2] if len(path) > 1 else None,
        }

    def _current_section_context(self, zone: str) -> Dict[str, Any]:
        stack = self._appendix_stack if zone == "appendix" else self._section_stack
        if not stack:
            return asdict(SectionContext())
        sid, title, level = stack[-1]
        return {
            "section_id": sid,
            "section_title": title,
            "section_level": level,
            "section_path": [x[0] for x in stack],
            "parent_section_id": stack[-2][0] if len(stack) > 1 else None,
        }

    @staticmethod
    def _summary(blocks: List[Dict[str, Any]], composite: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        return {
            "total_blocks": len(blocks),
            "total_sections": sum(1 for b in blocks if b["block_type"] == "heading"),
            "total_appendix_sections": sum(1 for b in blocks if b["block_type"] == "appendix_heading"),
            "total_tables": len(composite["tables"]),
            "total_figures": len(composite["figures"]),
            "total_formulas": len(composite["formulas"]),
            "total_notes": len(composite["notes"]),
            "total_list_items": sum(1 for b in blocks if b["block_type"] == "list_item"),
            "total_template_instructions": sum(1 for b in blocks if b["flags"]["is_template_instruction"]),
        }

    @staticmethod
    def _pseudo_hash(file_name: str) -> str:
        digest = hashlib.sha256(file_name.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    @staticmethod
    def _generate_document_id(file_name: str) -> str:
        digest = hashlib.sha1(file_name.encode("utf-8")).hexdigest()[:8].upper()
        return f"DOC_{datetime.now().year}_{digest}"
