from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RequirementCandidate(BaseModel):
    candidate_id: str
    source_block_ids: list[str] = Field(default_factory=list)
    primary_block_id: str
    section_path: list[str] = Field(default_factory=list)
    document_zone: str
    candidate_text: str
    extraction_reason: str
    confidence: float | str
    requirement_kind: str | None = None
    compact_section_path: str | None = None

    model_config = ConfigDict(extra="forbid")
