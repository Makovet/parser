from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AuditQuestion(BaseModel):
    question_id: str
    source_applied_requirement_id: str
    source_atomic_id: str | None = None
    source_requirement_id: str
    source_candidate_id: str
    source_block_ids: list[str] = Field(default_factory=list)
    document_zone: str
    section_path: list[str] = Field(default_factory=list)
    compact_section_path: str | None = None
    question_text: str
    question_type: str
    requirement_kind: str | None = None
    generation_reason: str
    traceability_chain: dict[str, str | list[str]] = Field(default_factory=dict)
    unresolved_dependencies: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class QuestionGenerationSummary(BaseModel):
    total_questions: int = 0
    generated_from_safe_atomic: int = 0
    skipped_context_only: int = 0
    skipped_unresolved: int = 0
    skipped_non_actionable: int = 0
    question_type_counts: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class QuestionGenerationReport(BaseModel):
    questions: list[AuditQuestion] = Field(default_factory=list)
    summary: QuestionGenerationSummary = Field(default_factory=QuestionGenerationSummary)

    model_config = ConfigDict(extra="forbid")
