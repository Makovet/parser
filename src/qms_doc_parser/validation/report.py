from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from qms_doc_parser.models.parser_models import BlockType, DocumentZone, ParserBlock, ParserDocument, ReviewCandidate
from qms_doc_parser.pipeline.parser_pipeline import parse_docx_to_document
from qms_doc_parser.review.review_candidates import build_review_candidates
from qms_doc_parser.validation.models import (
    ContractFieldSpec,
    ValidationCheckResult,
    ValidationReport,
    ValidationStatus,
)

PARSER_DOCUMENT_CONTRACT = [
    ContractFieldSpec(path="ParserDocument.structure_summary", notes="Stable aggregate counters for downstream gating."),
    ContractFieldSpec(path="ParserDocument.blocks", notes="Stable ordered block stream for downstream processing."),
    ContractFieldSpec(path="ParserBlock.block_id", notes="Stable block identifier used for cross-links."),
    ContractFieldSpec(path="ParserBlock.block_type", notes="Stable block label from BlockType enum."),
    ContractFieldSpec(path="ParserBlock.document_zone", notes="Stable zone label from DocumentZone enum."),
    ContractFieldSpec(path="ParserBlock.section_context", notes="Stable section lineage context for structural consumers."),
    ContractFieldSpec(path="ParserBlock.prev_block_id", notes="Stable adjacency link populated for review/downstream traversal."),
    ContractFieldSpec(path="ParserBlock.next_block_id", notes="Stable adjacency link populated for review/downstream traversal."),
    ContractFieldSpec(path="ParserBlock.review_features", notes="Stable review-friendly structural features."),
    ContractFieldSpec(path="ParserBlock.table_info", required=False, notes="Required for table blocks; downstream table consumers rely on it."),
    ContractFieldSpec(path="ParserBlock.note_info", required=False, notes="Optional typed note object; note-related metadata and block types remain stable."),
    ContractFieldSpec(path="ParserBlock.metadata.note_group_id", required=False, notes="Stable note grouping metadata when note grouping applies."),
    ContractFieldSpec(path="ParserBlock.metadata.is_orphan", required=False, notes="Stable note orphan marker used by review validation."),
]

REVIEW_CANDIDATE_CONTRACT = [
    ContractFieldSpec(path="ReviewCandidate.candidate_id", notes="Stable candidate identifier."),
    ContractFieldSpec(path="ReviewCandidate.block_id", notes="Stable link back to ParserBlock.block_id."),
    ContractFieldSpec(path="ReviewCandidate.current_block_type", notes="Stable current block type for reviewer routing."),
    ContractFieldSpec(path="ReviewCandidate.reason_codes", notes="Stable machine-readable reason labels."),
    ContractFieldSpec(path="ReviewCandidate.selected_features", notes="Stable selected review features payload."),
]


CheckFn = Callable[[ParserDocument], ValidationCheckResult]


def validate_parser_output(document: ParserDocument) -> ValidationReport:
    checks: list[ValidationCheckResult] = []
    for check in _CHECKS:
        checks.append(check(document))

    review_candidates, review_error = _build_review_candidates_safely(document.blocks)
    if review_error is None:
        checks.append(
            ValidationCheckResult(
                name="review_candidates_build",
                status=ValidationStatus.passed,
                message="Review candidates built successfully.",
                details={"candidate_count": len(review_candidates)},
            )
        )
        checks.append(_validate_review_candidates(document.blocks, review_candidates))
    else:
        checks.append(
            ValidationCheckResult(
                name="review_candidates_build",
                status=ValidationStatus.failed,
                message="Review candidates failed to build.",
                details={"error": review_error},
            )
        )
        checks.append(
            ValidationCheckResult(
                name="review_candidates_links",
                status=ValidationStatus.failed,
                message="Review candidates link validation skipped because candidate build failed.",
                details={},
            )
        )

    downstream_ready = all(check.status != ValidationStatus.failed for check in checks)
    metrics = {
        "total_checks": len(checks),
        "passed_checks": sum(1 for check in checks if check.status == ValidationStatus.passed),
        "warning_checks": sum(1 for check in checks if check.status == ValidationStatus.warning),
        "failed_checks": sum(1 for check in checks if check.status == ValidationStatus.failed),
        "total_blocks": len(document.blocks),
        "review_candidate_count": len(review_candidates),
    }

    return ValidationReport(
        document_id=document.document_id,
        template_id=document.template_id,
        parser_contract=list(PARSER_DOCUMENT_CONTRACT),
        review_candidate_contract=list(REVIEW_CANDIDATE_CONTRACT),
        checks=checks,
        metrics=metrics,
        downstream_ready=downstream_ready,
    )


def validate_docx_file(input_path: str | Path, registry_path: str | Path) -> ValidationReport:
    parsed = parse_docx_to_document(input_path=input_path, registry_path=registry_path)
    return validate_parser_output(parsed)


def _check_non_empty_document(document: ParserDocument) -> ValidationCheckResult:
    total_blocks = len(document.blocks)
    status = ValidationStatus.passed if total_blocks > 0 else ValidationStatus.failed
    return ValidationCheckResult(
        name="non_empty_document",
        status=status,
        message="Document contains parser blocks." if total_blocks > 0 else "Document contains no parser blocks.",
        details={"total_blocks": total_blocks},
    )


def _check_structure_summary(document: ParserDocument) -> ValidationCheckResult:
    summary = document.structure_summary
    actual = {
        "total_blocks": len(document.blocks),
        "total_tables": sum(1 for block in document.blocks if block.block_type == BlockType.table),
        "total_list_items": sum(1 for block in document.blocks if block.block_type == BlockType.list_item),
        "total_template_instructions": sum(1 for block in document.blocks if block.block_type == BlockType.template_instruction),
        "total_sections": sum(1 for block in document.blocks if block.block_type == BlockType.heading),
        "total_appendix_sections": sum(1 for block in document.blocks if block.block_type == BlockType.appendix_heading),
        "total_figures": sum(1 for block in document.blocks if block.block_type == BlockType.figure),
        "total_formulas": sum(1 for block in document.blocks if block.block_type == BlockType.formula),
        "total_notes": sum(1 for block in document.blocks if block.block_type in {BlockType.note_label, BlockType.note_text, BlockType.note_like}),
    }
    expected = {key: getattr(summary, key) for key in actual}
    mismatches = {key: {"expected": expected[key], "actual": actual[key]} for key in actual if expected[key] != actual[key]}
    return ValidationCheckResult(
        name="structure_summary_consistency",
        status=ValidationStatus.passed if not mismatches else ValidationStatus.failed,
        message="Structure summary is consistent with block stream." if not mismatches else "Structure summary counters are inconsistent with block stream.",
        details={"mismatches": mismatches, "summary": expected, "actual": actual},
    )


def _check_enum_values(document: ParserDocument) -> ValidationCheckResult:
    invalid_block_types = [block.block_id for block in document.blocks if block.block_type not in BlockType]
    invalid_zones = [block.block_id for block in document.blocks if block.document_zone not in DocumentZone]
    status = ValidationStatus.passed if not invalid_block_types and not invalid_zones else ValidationStatus.failed
    return ValidationCheckResult(
        name="enum_domain_validity",
        status=status,
        message="All block types and document zones are valid." if status == ValidationStatus.passed else "Some block types or document zones are invalid.",
        details={"invalid_block_types": invalid_block_types, "invalid_document_zones": invalid_zones},
    )


def _check_adjacent_links(document: ParserDocument) -> ValidationCheckResult:
    mismatches: list[dict[str, Any]] = []
    for index, block in enumerate(document.blocks):
        expected_prev = document.blocks[index - 1].block_id if index > 0 else None
        expected_next = document.blocks[index + 1].block_id if index + 1 < len(document.blocks) else None
        if block.prev_block_id != expected_prev or block.next_block_id != expected_next:
            mismatches.append(
                {
                    "block_id": block.block_id,
                    "expected_prev": expected_prev,
                    "actual_prev": block.prev_block_id,
                    "expected_next": expected_next,
                    "actual_next": block.next_block_id,
                }
            )
    return ValidationCheckResult(
        name="adjacent_block_links",
        status=ValidationStatus.passed if not mismatches else ValidationStatus.failed,
        message="Block adjacency links are consistent." if not mismatches else "Some prev/next block links are inconsistent.",
        details={"mismatched_blocks": mismatches},
    )


def _check_table_blocks(document: ParserDocument) -> ValidationCheckResult:
    issues: list[dict[str, Any]] = []
    for block in document.blocks:
        if block.block_type != BlockType.table:
            continue
        table_info = block.table_info
        if table_info is None:
            issues.append({"block_id": block.block_id, "issue": "missing_table_info"})
            continue
        if table_info.table_index is None or table_info.rows_count is None or table_info.cols_count is None:
            issues.append({"block_id": block.block_id, "issue": "incomplete_table_info"})
    return ValidationCheckResult(
        name="table_block_payloads",
        status=ValidationStatus.passed if not issues else ValidationStatus.failed,
        message="All table blocks expose required table_info payloads." if not issues else "Some table blocks are missing required table payload fields.",
        details={"issues": issues},
    )


def _check_note_blocks(document: ParserDocument) -> ValidationCheckResult:
    issues: list[dict[str, Any]] = []
    note_types = {BlockType.note_label, BlockType.note_text, BlockType.note_like}
    for block in document.blocks:
        if block.block_type not in note_types:
            continue
        if block.review_features is None:
            issues.append({"block_id": block.block_id, "issue": "missing_review_features"})
        metadata = getattr(block, "metadata", None)
        if block.block_type in {BlockType.note_label, BlockType.note_text} and metadata is not None and not isinstance(metadata, dict):
            issues.append({"block_id": block.block_id, "issue": "invalid_note_metadata"})
    return ValidationCheckResult(
        name="note_block_review_readiness",
        status=ValidationStatus.passed if not issues else ValidationStatus.failed,
        message="Note-related blocks are structurally ready for review/downstream use." if not issues else "Some note-related blocks have broken review metadata/features.",
        details={"issues": issues},
    )


def _check_section_context(document: ParserDocument) -> ValidationCheckResult:
    issues: list[dict[str, Any]] = []
    structural_types = {BlockType.heading, BlockType.appendix_heading, BlockType.paragraph, BlockType.list_item, BlockType.table}
    contextual_zones = {DocumentZone.main_body, DocumentZone.appendix}
    for block in document.blocks:
        if block.block_type not in structural_types or block.document_zone not in contextual_zones:
            continue
        context = block.section_context
        if block.block_type in {BlockType.heading, BlockType.appendix_heading} and not context.section_id:
            issues.append({"block_id": block.block_id, "issue": "missing_section_id"})
        if context.section_path and context.section_id and context.section_path[-1] != context.section_id:
            issues.append({"block_id": block.block_id, "issue": "section_path_tail_mismatch"})
    return ValidationCheckResult(
        name="section_context_validity",
        status=ValidationStatus.passed if not issues else ValidationStatus.failed,
        message="Section context is structurally valid for downstream use." if not issues else "Some structural blocks have invalid section context.",
        details={"issues": issues},
    )


def _validate_review_candidates(blocks: list[ParserBlock], candidates: list[ReviewCandidate]) -> ValidationCheckResult:
    block_ids = {block.block_id for block in blocks}
    issues: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.block_id not in block_ids:
            issues.append({"candidate_id": candidate.candidate_id, "issue": "unknown_block_id", "block_id": candidate.block_id})
    return ValidationCheckResult(
        name="review_candidates_links",
        status=ValidationStatus.passed if not issues else ValidationStatus.failed,
        message="Review candidates link to parser blocks correctly." if not issues else "Some review candidates reference unknown parser blocks.",
        details={"issues": issues, "candidate_count": len(candidates)},
    )


def _build_review_candidates_safely(blocks: list[ParserBlock]) -> tuple[list[ReviewCandidate], str | None]:
    try:
        return build_review_candidates(blocks), None
    except Exception as exc:  # pragma: no cover - defensive surface for harness
        return [], f"{type(exc).__name__}: {exc}"


_CHECKS: tuple[CheckFn, ...] = (
    _check_non_empty_document,
    _check_structure_summary,
    _check_enum_values,
    _check_adjacent_links,
    _check_table_blocks,
    _check_note_blocks,
    _check_section_context,
)
