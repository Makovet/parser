from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ValidationStatus(str, Enum):
    passed = "passed"
    failed = "failed"
    warning = "warning"


class ContractFieldSpec(BaseModel):
    path: str
    stability: str = "stable"
    required: bool = True
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class ValidationCheckResult(BaseModel):
    name: str
    status: ValidationStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ValidationReport(BaseModel):
    document_id: str | None = None
    template_id: str | None = None
    parser_contract: list[ContractFieldSpec] = Field(default_factory=list)
    review_candidate_contract: list[ContractFieldSpec] = Field(default_factory=list)
    checks: list[ValidationCheckResult] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    downstream_ready: bool = False

    model_config = ConfigDict(extra="forbid")


class BatchValidationDocumentResult(BaseModel):
    input_path: str
    report_path: str | None = None
    report: ValidationReport | None = None
    status: ValidationStatus
    message: str

    model_config = ConfigDict(extra="forbid")


class BatchValidationSummary(BaseModel):
    total_documents: int = 0
    passed_documents: int = 0
    failed_documents: int = 0
    warnings_count: int = 0
    common_failed_checks: dict[str, int] = Field(default_factory=dict)
    common_warning_checks: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class BatchValidationReport(BaseModel):
    input_paths: list[str] = Field(default_factory=list)
    documents: list[BatchValidationDocumentResult] = Field(default_factory=list)
    summary: BatchValidationSummary = Field(default_factory=BatchValidationSummary)

    model_config = ConfigDict(extra="forbid")
