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
    revised_atomic_text: str | None = None
    revised_subject_hint: str | None = None
    revised_action_hint: str | None = None
    revised_object_hint: str | None = None
    revised_condition_hint: str | None = None
    confidence: float | str

    model_config = ConfigDict(extra="forbid")


class AppliedAtomicRequirement(BaseModel):
    applied_atomic_id: str
    source_atomic_id: str | None = None
    atomic_text: str
    applied_atomic_text: str | None = None
    subject_hint: str | None = None
    action_hint: str | None = None
    object_hint: str | None = None
    condition_hint: str | None = None
    source_span_type: str
    confidence: float | str
    applied_operations: list[str] = Field(default_factory=list)
    unresolved_review_flags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class AppliedRequirementRecord(BaseModel):
    applied_requirement_id: str
    source_requirement_id: str
    source_candidate_id: str
    source_block_ids: list[str] = Field(default_factory=list)
    primary_block_id: str
    document_zone: str
    section_path: list[str] = Field(default_factory=list)
    compact_section_path: str | None = None
    original_text: str
    normalized_text: str
    applied_text: str | None = None
    requirement_kind: str | None = None
    decomposition_strategy: str
    atomic_requirements: list[AppliedAtomicRequirement] = Field(default_factory=list)
    applied_operations: list[str] = Field(default_factory=list)
    unresolved_review_flags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class RequirementApplyDecision(BaseModel):
    apply_decision_id: str
    source_review_decision_id: str | None = None
    source_requirement_id: str
    apply_policy: str
    selected_operation: str
    applied: bool = False
    target_atomic_ids: list[str] = Field(default_factory=list)
    unresolved_review_flags: list[str] = Field(default_factory=list)
    message: str

    model_config = ConfigDict(extra="forbid")


class RequirementApplySummary(BaseModel):
    total_review_decisions: int = 0
    auto_applicable_decisions: int = 0
    applied_decisions: int = 0
    unresolved_decisions: int = 0
    unsupported_decisions: int = 0
    operation_counts: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class RequirementApplyReport(BaseModel):
    apply_decisions: list[RequirementApplyDecision] = Field(default_factory=list)
    summary: RequirementApplySummary = Field(default_factory=RequirementApplySummary)

    model_config = ConfigDict(extra="forbid")
