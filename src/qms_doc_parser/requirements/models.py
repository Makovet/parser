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


class AtomicRequirement(BaseModel):
    atomic_id: str
    atomic_text: str
    subject_hint: str | None = None
    action_hint: str | None = None
    object_hint: str | None = None
    condition_hint: str | None = None
    source_span_type: str
    confidence: float | str

    model_config = ConfigDict(extra="forbid")


class RequirementRecord(BaseModel):
    requirement_id: str
    source_candidate_id: str
    source_block_ids: list[str] = Field(default_factory=list)
    primary_block_id: str
    document_zone: str
    section_path: list[str] = Field(default_factory=list)
    compact_section_path: str | None = None
    original_text: str
    normalized_text: str
    requirement_kind: str | None = None
    decomposition_strategy: str
    atomic_requirements: list[AtomicRequirement] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class RequirementReviewCase(BaseModel):
    review_case_id: str
    requirement_id: str
    source_candidate_id: str
    primary_block_id: str
    section_path: list[str] = Field(default_factory=list)
    compact_section_path: str | None = None
    decomposition_strategy: str
    ambiguity_type: str
    reason_codes: list[str] = Field(default_factory=list)
    context_requirement_ids: list[str] = Field(default_factory=list)
    current_text: str
    context_texts: list[str] = Field(default_factory=list)
    selected_features: dict[str, object] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class RequirementReviewDecision(BaseModel):
    decision_id: str
    review_case_id: str
    requirement_id: str
    decision_label: str
    resolution_summary: str
    decision_source: str = "deterministic_baseline"
    target_atomic_ids: list[str] = Field(default_factory=list)
    reviewer_action: str | None = None
    confidence: float | str

    model_config = ConfigDict(extra="forbid")
