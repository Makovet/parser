from __future__ import annotations

from collections import Counter

from qms_doc_parser.requirements.models import (
    AppliedAtomicRequirement,
    AppliedRequirementRecord,
    RequirementApplyDecision,
    RequirementApplyReport,
    RequirementApplySummary,
    RequirementRecord,
    RequirementReviewDecision,
)

_AUTO_APPLICABLE_OPERATIONS = {
    "apply_subject_from_parent_context",
    "mark_context_only",
    "keep_as_is",
}
_REVISED_CONTENT_OPERATIONS = {"apply_revised_atomic_text", "apply_hint_cleanup"}
_REQUIRES_HUMAN_OPERATIONS = {
    "confirm_missing_list_items",
    "verify_split_sentence_scope",
    "check_condition_attachment",
}


def apply_requirement_review_decisions(
    records: list[RequirementRecord],
    review_decisions: list[RequirementReviewDecision],
) -> tuple[list[AppliedRequirementRecord], RequirementApplyReport]:
    applied_records = [_make_applied_record(record, index + 1) for index, record in enumerate(records)]
    applied_by_requirement_id = {record.source_requirement_id: record for record in applied_records}
    source_by_requirement_id = {record.requirement_id: record for record in records}

    apply_decisions: list[RequirementApplyDecision] = []
    operation_counts: Counter[str] = Counter()

    for index, review_decision in enumerate(review_decisions):
        policy = classify_requirement_apply_policy(review_decision)
        applied_record = applied_by_requirement_id.get(review_decision.requirement_id)
        source_record = source_by_requirement_id.get(review_decision.requirement_id)
        if applied_record is None or source_record is None:
            apply_decisions.append(
                RequirementApplyDecision(
                    apply_decision_id=f"reqap_{index + 1:04d}",
                    source_review_decision_id=review_decision.decision_id,
                    source_requirement_id=review_decision.requirement_id,
                    apply_policy="unsupported_for_apply_v0_1",
                    selected_operation=review_decision.reviewer_action or "unknown_operation",
                    applied=False,
                    target_atomic_ids=list(review_decision.target_atomic_ids),
                    unresolved_review_flags=["missing_source_requirement"],
                    message="Apply layer could not find the source requirement record for this review decision.",
                )
            )
            operation_counts["attach_review_flag"] += 1
            continue

        if policy == "auto_applicable":
            applied, message, operations, unresolved_flags = _apply_safe_decision(
                applied_record,
                source_record,
                records,
                review_decision,
            )
            _append_unique(applied_record.applied_operations, operations)
            _append_unique(applied_record.unresolved_review_flags, unresolved_flags)
            operation_counts.update(operations)
        else:
            applied = False
            operations = ["attach_review_flag"]
            operation_counts.update(operations)
            unresolved_flags = [review_decision.reviewer_action or review_decision.decision_label]
            _append_unique(applied_record.unresolved_review_flags, unresolved_flags)
            message = "Review decision remains unresolved in apply layer."

        apply_decisions.append(
            RequirementApplyDecision(
                apply_decision_id=f"reqap_{index + 1:04d}",
                source_review_decision_id=review_decision.decision_id,
                source_requirement_id=review_decision.requirement_id,
                apply_policy=policy,
                selected_operation=review_decision.reviewer_action or "unknown_operation",
                applied=applied,
                target_atomic_ids=list(review_decision.target_atomic_ids),
                unresolved_review_flags=unresolved_flags,
                message=message,
            )
        )

    _mark_records_without_decisions(applied_records, source_by_requirement_id, review_decisions, operation_counts)

    summary = RequirementApplySummary(
        total_review_decisions=len(review_decisions),
        auto_applicable_decisions=sum(1 for decision in apply_decisions if decision.apply_policy == "auto_applicable"),
        applied_decisions=sum(1 for decision in apply_decisions if decision.applied),
        unresolved_decisions=sum(1 for decision in apply_decisions if decision.apply_policy == "requires_human_review"),
        unsupported_decisions=sum(1 for decision in apply_decisions if decision.apply_policy == "unsupported_for_apply_v0_1"),
        operation_counts=dict(sorted(operation_counts.items())),
    )
    return applied_records, RequirementApplyReport(apply_decisions=apply_decisions, summary=summary)


def classify_requirement_apply_policy(review_decision: RequirementReviewDecision) -> str:
    operation = review_decision.reviewer_action
    if operation in _AUTO_APPLICABLE_OPERATIONS:
        return "auto_applicable"
    if operation in _REVISED_CONTENT_OPERATIONS and _has_explicit_safe_payload(review_decision):
        return "auto_applicable"
    if operation in _REQUIRES_HUMAN_OPERATIONS or review_decision.decision_label == "needs_human_review":
        return "requires_human_review"
    return "unsupported_for_apply_v0_1"


def _make_applied_record(record: RequirementRecord, index: int) -> AppliedRequirementRecord:
    return AppliedRequirementRecord(
        applied_requirement_id=f"appr_{index:04d}",
        source_requirement_id=record.requirement_id,
        source_candidate_id=record.source_candidate_id,
        source_block_ids=list(record.source_block_ids),
        primary_block_id=record.primary_block_id,
        document_zone=record.document_zone,
        section_path=list(record.section_path),
        compact_section_path=record.compact_section_path,
        original_text=record.original_text,
        normalized_text=record.normalized_text,
        applied_text=None,
        requirement_kind=record.requirement_kind,
        decomposition_strategy=record.decomposition_strategy,
        atomic_requirements=[
            AppliedAtomicRequirement(
                applied_atomic_id=f"{atomic.atomic_id}_applied",
                source_atomic_id=atomic.atomic_id,
                atomic_text=atomic.atomic_text,
                applied_atomic_text=None,
                subject_hint=atomic.subject_hint,
                action_hint=atomic.action_hint,
                object_hint=atomic.object_hint,
                condition_hint=atomic.condition_hint,
                source_span_type=atomic.source_span_type,
                confidence=atomic.confidence,
            )
            for atomic in record.atomic_requirements
        ],
    )


def _apply_safe_decision(
    applied_record: AppliedRequirementRecord,
    source_record: RequirementRecord,
    all_records: list[RequirementRecord],
    review_decision: RequirementReviewDecision,
) -> tuple[bool, str, list[str], list[str]]:
    operation = review_decision.reviewer_action or "unknown_operation"

    if operation == "mark_context_only":
        return True, "Requirement preserved as context-only.", ["mark_context_only"], []

    if operation == "apply_subject_from_parent_context":
        inherited_subject = _resolve_parent_subject(source_record, all_records)
        if inherited_subject is None:
            unresolved_flag = "apply_subject_from_parent_context_unresolved"
            _append_unique(applied_record.unresolved_review_flags, [unresolved_flag])
            return False, "Parent context subject was not found; no automatic inheritance was applied.", ["attach_review_flag"], [unresolved_flag]

        operations: list[str] = []
        for atomic in applied_record.atomic_requirements:
            if review_decision.target_atomic_ids and atomic.source_atomic_id not in review_decision.target_atomic_ids:
                continue
            atomic.subject_hint = inherited_subject
            _append_unique(atomic.applied_operations, ["apply_subject_from_parent_context"])
            operations.append("apply_subject_from_parent_context")
        return True, "Subject inherited safely from parent context.", _dedupe(operations), []

    if operation == "keep_as_is":
        return True, "Requirement kept as-is by explicit safe decision.", ["keep_as_is"], []

    if operation == "apply_revised_atomic_text":
        target_atomic = _find_single_target_atomic(applied_record, review_decision)
        if target_atomic is None or review_decision.revised_atomic_text is None:
            unresolved_flag = "apply_revised_atomic_text_unresolved"
            _append_unique(applied_record.unresolved_review_flags, [unresolved_flag])
            return False, "Explicit revised atomic text was missing or ambiguous.", ["attach_review_flag"], [unresolved_flag]
        target_atomic.applied_atomic_text = review_decision.revised_atomic_text
        _append_unique(target_atomic.applied_operations, ["apply_revised_atomic_text"])
        if len(applied_record.atomic_requirements) == 1:
            applied_record.applied_text = review_decision.revised_atomic_text
        return True, "Explicit revised atomic text was applied safely.", ["apply_revised_atomic_text"], []

    if operation == "apply_hint_cleanup":
        target_atomic = _find_single_target_atomic(applied_record, review_decision)
        if target_atomic is None or not _has_explicit_hint_payload(review_decision):
            unresolved_flag = "apply_hint_cleanup_unresolved"
            _append_unique(applied_record.unresolved_review_flags, [unresolved_flag])
            return False, "Explicit revised hints were missing or ambiguous.", ["attach_review_flag"], [unresolved_flag]
        if review_decision.revised_subject_hint is not None:
            target_atomic.subject_hint = review_decision.revised_subject_hint
        if review_decision.revised_action_hint is not None:
            target_atomic.action_hint = review_decision.revised_action_hint
        if review_decision.revised_object_hint is not None:
            target_atomic.object_hint = review_decision.revised_object_hint
        if review_decision.revised_condition_hint is not None:
            target_atomic.condition_hint = review_decision.revised_condition_hint
        _append_unique(target_atomic.applied_operations, ["apply_hint_cleanup"])
        return True, "Explicit hint cleanup was applied safely.", ["apply_hint_cleanup"], []

    unresolved_flag = f"{operation}_unsupported"
    _append_unique(applied_record.unresolved_review_flags, [unresolved_flag])
    return False, "Decision is not supported for automatic apply in v0.1.", ["attach_review_flag"], [unresolved_flag]


def _resolve_parent_subject(record: RequirementRecord, records: list[RequirementRecord]) -> str | None:
    record_index = next((index for index, candidate in enumerate(records) if candidate.requirement_id == record.requirement_id), None)
    if record_index is None:
        return None
    for previous_index in range(record_index - 1, -1, -1):
        previous_record = records[previous_index]
        if previous_record.section_path != record.section_path:
            continue
        if previous_record.decomposition_strategy != "list_header_context":
            continue
        if previous_record.normalized_text:
            subject = _extract_subject_from_context_text(previous_record.normalized_text)
            if subject:
                return subject
        if previous_record.atomic_requirements:
            subject_hint = previous_record.atomic_requirements[0].subject_hint
            if subject_hint:
                return subject_hint
    return None


def _find_single_target_atomic(
    applied_record: AppliedRequirementRecord,
    review_decision: RequirementReviewDecision,
) -> AppliedAtomicRequirement | None:
    if len(review_decision.target_atomic_ids) != 1:
        return None
    target_atomic_id = review_decision.target_atomic_ids[0]
    return next((atomic for atomic in applied_record.atomic_requirements if atomic.source_atomic_id == target_atomic_id), None)


def _has_explicit_safe_payload(review_decision: RequirementReviewDecision) -> bool:
    if review_decision.reviewer_action == "apply_revised_atomic_text":
        return review_decision.revised_atomic_text is not None and len(review_decision.target_atomic_ids) == 1
    if review_decision.reviewer_action == "apply_hint_cleanup":
        return len(review_decision.target_atomic_ids) == 1 and _has_explicit_hint_payload(review_decision)
    return False


def _has_explicit_hint_payload(review_decision: RequirementReviewDecision) -> bool:
    return any(
        value is not None
        for value in (
            review_decision.revised_subject_hint,
            review_decision.revised_action_hint,
            review_decision.revised_object_hint,
            review_decision.revised_condition_hint,
        )
    )


def _mark_records_without_decisions(
    applied_records: list[AppliedRequirementRecord],
    source_by_requirement_id: dict[str, RequirementRecord],
    review_decisions: list[RequirementReviewDecision],
    operation_counts: Counter[str],
) -> None:
    decision_requirement_ids = {decision.requirement_id for decision in review_decisions}
    for applied_record in applied_records:
        if applied_record.source_requirement_id in decision_requirement_ids:
            continue
        _append_unique(applied_record.applied_operations, ["keep_as_is"])
        source_record = source_by_requirement_id[applied_record.source_requirement_id]
        for applied_atomic in applied_record.atomic_requirements:
            if applied_atomic.source_atomic_id is not None:
                _append_unique(applied_atomic.applied_operations, ["keep_as_is"])
        operation_counts["keep_as_is"] += 1


def _extract_subject_from_context_text(text: str) -> str | None:
    lowered = text.lower()
    markers = (" должен ", " должна ", " должны ", " обязан ", " обязана ", " обязаны ", " необходимо ", " следует ", " подлежит ")
    for marker in markers:
        marker_index = lowered.find(marker)
        if marker_index >= 0:
            subject = text[:marker_index].strip(" ,")
            return subject or None
    return None


def _append_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
