from __future__ import annotations

from qms_doc_parser.requirements.models import (
    RequirementRecord,
    RequirementReviewCase,
    RequirementReviewDecision,
)


def build_requirement_review_cases(records: list[RequirementRecord]) -> list[RequirementReviewCase]:
    review_cases: list[RequirementReviewCase] = []

    for index, record in enumerate(records):
        ambiguity_type, reason_codes = _detect_ambiguity(records, index)
        if ambiguity_type is None:
            continue

        context_records = _resolve_context_records(records, index, ambiguity_type)
        review_cases.append(
            RequirementReviewCase(
                review_case_id=f"reqv_{len(review_cases) + 1:04d}",
                requirement_id=record.requirement_id,
                source_candidate_id=record.source_candidate_id,
                primary_block_id=record.primary_block_id,
                section_path=list(record.section_path),
                compact_section_path=record.compact_section_path,
                decomposition_strategy=record.decomposition_strategy,
                ambiguity_type=ambiguity_type,
                reason_codes=reason_codes,
                context_requirement_ids=[context.requirement_id for context in context_records],
                current_text=record.normalized_text,
                context_texts=[context.normalized_text for context in context_records],
                selected_features=_selected_features(record, context_records),
            )
        )

    return review_cases


def build_requirement_review_decisions(
    review_cases: list[RequirementReviewCase],
    records: list[RequirementRecord],
) -> list[RequirementReviewDecision]:
    records_by_id = {record.requirement_id: record for record in records}
    decisions: list[RequirementReviewDecision] = []

    for index, case in enumerate(review_cases):
        record = records_by_id[case.requirement_id]
        decision_label, reviewer_action, resolution_summary, confidence = _baseline_decision(case, record)
        decisions.append(
            RequirementReviewDecision(
                decision_id=f"reqd_{index + 1:04d}",
                review_case_id=case.review_case_id,
                requirement_id=case.requirement_id,
                decision_label=decision_label,
                resolution_summary=resolution_summary,
                target_atomic_ids=[atomic.atomic_id for atomic in record.atomic_requirements],
                reviewer_action=reviewer_action,
                confidence=confidence,
            )
        )

    return decisions


def _detect_ambiguity(records: list[RequirementRecord], index: int) -> tuple[str | None, list[str]]:
    record = records[index]

    if record.decomposition_strategy == "list_header_context":
        next_record = records[index + 1] if index + 1 < len(records) else None
        if next_record and next_record.decomposition_strategy == "contextual_list_item" and next_record.section_path == record.section_path:
            return "requires_list_item_context", ["list_header_without_atomic", "followed_by_contextual_items"]
        return "dangling_list_header", ["list_header_without_atomic", "missing_contextual_items"]

    if record.decomposition_strategy == "contextual_list_item":
        atomic = record.atomic_requirements[0] if record.atomic_requirements else None
        if atomic and atomic.subject_hint is None:
            return "missing_subject_context", ["contextual_list_item", "subject_hint_missing"]

    if record.decomposition_strategy == "sentence_split":
        if any(atomic.subject_hint is None for atomic in record.atomic_requirements):
            return "mixed_subject_scope", ["sentence_split", "subject_hint_missing_in_atomic"]

    if record.decomposition_strategy == "semicolon_split":
        if any(atomic.condition_hint is not None for atomic in record.atomic_requirements):
            return "conditional_clause_scope", ["semicolon_split", "conditional_clause_present"]

    return None, []


def _resolve_context_records(
    records: list[RequirementRecord],
    index: int,
    ambiguity_type: str,
) -> list[RequirementRecord]:
    record = records[index]
    context_records: list[RequirementRecord] = []

    if ambiguity_type == "requires_list_item_context":
        next_index = index + 1
        while next_index < len(records):
            next_record = records[next_index]
            if next_record.decomposition_strategy != "contextual_list_item" or next_record.section_path != record.section_path:
                break
            context_records.append(next_record)
            next_index += 1
        return context_records

    previous_record = records[index - 1] if index > 0 else None
    if previous_record and previous_record.section_path == record.section_path:
        context_records.append(previous_record)
    return context_records


def _selected_features(record: RequirementRecord, context_records: list[RequirementRecord]) -> dict[str, object]:
    return {
        "atomic_count": len(record.atomic_requirements),
        "requirement_kind": record.requirement_kind,
        "has_context_records": bool(context_records),
        "context_record_count": len(context_records),
    }


def _baseline_decision(
    review_case: RequirementReviewCase,
    record: RequirementRecord,
) -> tuple[str, str | None, str, float]:
    if review_case.ambiguity_type == "requires_list_item_context":
        return (
            "needs_human_review",
            "link_header_to_list_items",
            "Header defines context for following list items and should be reviewed without auto-applying a merge.",
            0.93,
        )
    if review_case.ambiguity_type == "dangling_list_header":
        return (
            "needs_human_review",
            "confirm_missing_list_items",
            "Header implies a list context, but matching contextual items were not found in the same section.",
            0.91,
        )
    if review_case.ambiguity_type == "missing_subject_context":
        return (
            "needs_human_review",
            "confirm_subject_from_context",
            "Contextual list item lacks its own explicit subject and should inherit scope only after review.",
            0.89,
        )
    if review_case.ambiguity_type == "mixed_subject_scope":
        return (
            "needs_human_review",
            "verify_split_sentence_scope",
            "Split sentence contains atomic requirements with incomplete subject hints.",
            0.84,
        )
    if review_case.ambiguity_type == "conditional_clause_scope":
        return (
            "review_recommended",
            "check_condition_attachment",
            "Conditional semicolon split may need a reviewer to confirm how the condition applies across clauses.",
            0.8,
        )

    return (
        "review_recommended",
        None,
        f"Deterministic reviewer flagged ambiguity for strategy {record.decomposition_strategy}.",
        0.75,
    )
