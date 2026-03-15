from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class StyleRule(BaseModel):
    block_type: str
    block_subtype: Optional[str] = None
    default_zone: str = "unknown_zone"
    heading_level: Optional[int] = None
    list_type: Optional[str] = None
    list_level: Optional[int] = None
    semantic_hints: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class ZoneDetectionRule(BaseModel):
    name: str
    when_styles: List[str] = Field(default_factory=list)
    when_text_equals: List[str] = Field(default_factory=list)
    when_text_contains: List[str] = Field(default_factory=list)
    preferred_styles: List[str] = Field(default_factory=list)
    assign_zone: str

    model_config = ConfigDict(extra="forbid")


class FallbackRules(BaseModel):
    heading_number_pattern: Optional[str] = None
    appendix_heading_pattern: Optional[str] = None
    numbered_list_pattern: Optional[str] = None
    lettered_list_pattern: Optional[str] = None
    bulleted_list_pattern: Optional[str] = None
    note_pattern: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CompositeObjectRules(BaseModel):
    table: Dict[str, List[str]] = Field(default_factory=dict)
    figure: Dict[str, List[str]] = Field(default_factory=dict)
    formula: Dict[str, List[str]] = Field(default_factory=dict)
    note: Dict[str, List[str]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class RegistrySettings(BaseModel):
    classification_mode: str = "style_first"
    fallback_to_text_patterns: bool = True
    detect_document_zones: bool = True
    keep_unknown_styles: bool = True
    collect_header_footer: bool = True
    build_composite_objects: bool = True

    model_config = ConfigDict(extra="forbid")


class StyleRegistryConfig(BaseModel):
    template_id: str
    version: str
    description: Optional[str] = None
    settings: RegistrySettings
    document_zones: List[str]
    block_types: List[str]
    style_registry: Dict[str, StyleRule]
    zone_detection_rules: List[ZoneDetectionRule] = Field(default_factory=list)
    fallback_rules: Optional[FallbackRules] = None
    composite_object_rules: Optional[CompositeObjectRules] = None

    model_config = ConfigDict(extra="forbid")