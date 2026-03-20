from __future__ import annotations

from collections import Counter

from qms_doc_parser.questions.models import AuditQuestion, QuestionGenerationReport, QuestionGenerationSummary
from qms_doc_parser.requirements.models import AppliedAtomicRequirement, AppliedRequirementRecord

_EVIDENCE_TERMS = (
    "зарегистр",
    "регистрац",
    "журнал",
    "запис",
    "документ",
    "оформл",
    "реестр",
)
_PROCESS_TERMS = (
    "контрол",
    "проведен",
    "процесс",
    "обеспеч",
    "выполня",
    "организ",
    "провер",
)
_NORMATIVE_KINDS = {"obligation", "contextual_obligation"}
_MIN_ACTIONABLE_WORDS = 2


def generate_audit_questions(applied_records: list[AppliedRequirementRecord]) -> QuestionGenerationReport:
    questions: list[AuditQuestion] = []
    summary = QuestionGenerationSummary()
    question_type_counts: Counter[str] = Counter()

    for record in applied_records:
        if "mark_context_only" in record.applied_operations and not record.atomic_requirements:
            summary.skipped_context_only += 1
            continue
        for atomic in record.atomic_requirements:
            eligibility, skip_reason = classify_question_generation_eligibility(record, atomic)
            if not eligibility:
                _increment_skip_counter(summary, skip_reason)
                continue

            question_text = _build_question_text(record, atomic)
            if question_text is None:
                summary.skipped_non_actionable += 1
                continue

            question_type = _classify_question_type(record, atomic)
            question_type_counts[question_type] += 1
            questions.append(
                AuditQuestion(
                    question_id=f"aq_{len(questions) + 1:04d}",
                    source_applied_requirement_id=record.applied_requirement_id,
                    source_atomic_id=atomic.source_atomic_id,
                    source_requirement_id=record.source_requirement_id,
                    source_candidate_id=record.source_candidate_id,
                    source_block_ids=list(record.source_block_ids),
                    document_zone=record.document_zone,
                    section_path=list(record.section_path),
                    compact_section_path=record.compact_section_path,
                    question_text=question_text,
                    question_type=question_type,
                    requirement_kind=record.requirement_kind,
                    generation_reason=f"safe_{question_type}",
                    traceability_chain={
                        "source_applied_requirement_id": record.applied_requirement_id,
                        "source_atomic_id": atomic.source_atomic_id or "",
                        "source_requirement_id": record.source_requirement_id,
                        "source_candidate_id": record.source_candidate_id,
                        "source_block_ids": list(record.source_block_ids),
                    },
                    unresolved_dependencies=list(dict.fromkeys(record.unresolved_review_flags + atomic.unresolved_review_flags)),
                )
            )

    summary.total_questions = len(questions)
    summary.generated_from_safe_atomic = len(questions)
    summary.question_type_counts = dict(sorted(question_type_counts.items()))
    return QuestionGenerationReport(questions=questions, summary=summary)


def classify_question_generation_eligibility(
    record: AppliedRequirementRecord,
    atomic: AppliedAtomicRequirement,
) -> tuple[bool, str | None]:
    if record.document_zone != "main_body":
        return False, "context_only"
    if "mark_context_only" in record.applied_operations:
        return False, "context_only"
    if record.unresolved_review_flags or atomic.unresolved_review_flags:
        return False, "unresolved"

    text = _effective_atomic_text(atomic).strip()
    words = text.split()
    if len(words) < _MIN_ACTIONABLE_WORDS:
        return False, "non_actionable"
    if not _has_actionable_content(record, atomic, text):
        return False, "non_actionable"
    return True, None


def _build_question_text(record: AppliedRequirementRecord, atomic: AppliedAtomicRequirement) -> str | None:
    text = _trim_terminal_punctuation(_effective_atomic_text(atomic))
    if not text:
        return None

    subject = _normalize_fragment(atomic.subject_hint)
    action = _normalize_fragment(atomic.action_hint)
    obj = _normalize_fragment(atomic.object_hint)

    question_type = _classify_question_type(record, atomic)
    if question_type == "evidence_check":
        return f"Как подтверждается {text.lower()}?"
    if question_type == "process_check":
        if action and obj:
            return f"Каким образом выполняется {action} {obj.lower()}?"
        return f"Как обеспечивается {text.lower()}?"
    if subject and action:
        tail = f" {obj.lower()}" if obj else ""
        return f"Каким образом {subject.lower()} {action.lower()}{tail}?"
    if action and obj:
        return f"Каким образом выполняется {action.lower()} {obj.lower()}?"
    return f"Как выполняется {text.lower()}?"


def _classify_question_type(record: AppliedRequirementRecord, atomic: AppliedAtomicRequirement) -> str:
    text = _effective_atomic_text(atomic).lower()
    if any(term in text for term in _EVIDENCE_TERMS):
        return "evidence_check"
    if any(term in text for term in _PROCESS_TERMS) or record.requirement_kind not in _NORMATIVE_KINDS:
        return "process_check"
    return "implementation_check"


def _effective_atomic_text(atomic: AppliedAtomicRequirement) -> str:
    return atomic.applied_atomic_text or atomic.atomic_text


def _has_actionable_content(
    record: AppliedRequirementRecord,
    atomic: AppliedAtomicRequirement,
    text: str,
) -> bool:
    if atomic.action_hint:
        return True
    lowered = text.lower()
    if record.requirement_kind in _NORMATIVE_KINDS and any(term in lowered for term in _EVIDENCE_TERMS + _PROCESS_TERMS):
        return True
    return False


def _increment_skip_counter(summary: QuestionGenerationSummary, skip_reason: str | None) -> None:
    if skip_reason == "context_only":
        summary.skipped_context_only += 1
    elif skip_reason == "unresolved":
        summary.skipped_unresolved += 1
    elif skip_reason == "non_actionable":
        summary.skipped_non_actionable += 1


def _trim_terminal_punctuation(text: str) -> str:
    return text.strip().rstrip(".;: ")


def _normalize_fragment(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _trim_terminal_punctuation(value).strip()
    return normalized or None
