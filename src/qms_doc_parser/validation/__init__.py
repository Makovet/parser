from qms_doc_parser.validation.batch import (
    aggregate_batch_results,
    build_batch_validation_report,
    discover_docx_inputs,
)
from qms_doc_parser.validation.models import (
    BatchValidationDocumentResult,
    BatchValidationReport,
    BatchValidationSummary,
    ContractFieldSpec,
    ValidationCheckResult,
    ValidationReport,
    ValidationStatus,
)
from qms_doc_parser.validation.report import (
    PARSER_DOCUMENT_CONTRACT,
    REVIEW_CANDIDATE_CONTRACT,
    validate_parser_output,
)

STABLE_PARSER_CONTRACT = PARSER_DOCUMENT_CONTRACT

__all__ = [
    "aggregate_batch_results",
    "BatchValidationDocumentResult",
    "BatchValidationReport",
    "BatchValidationSummary",
    "build_batch_validation_report",
    "ContractFieldSpec",
    "discover_docx_inputs",
    "PARSER_DOCUMENT_CONTRACT",
    "REVIEW_CANDIDATE_CONTRACT",
    "STABLE_PARSER_CONTRACT",
    "ValidationCheckResult",
    "ValidationReport",
    "ValidationStatus",
    "validate_parser_output",
]
