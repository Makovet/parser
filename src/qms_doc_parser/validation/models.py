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
