from __future__ import annotations

from collections import Counter
from pathlib import Path

from qms_doc_parser.validation.models import (
    BatchValidationDocumentResult,
    BatchValidationReport,
    BatchValidationSummary,
    ValidationStatus,
)
from qms_doc_parser.validation.report import validate_docx_file


def discover_docx_inputs(paths: list[str] | None = None, input_dir: str | Path | None = None) -> tuple[list[Path], list[BatchValidationDocumentResult]]:
    discovered: list[Path] = []
    issues: list[BatchValidationDocumentResult] = []

    for raw_path in paths or []:
        path = Path(raw_path)
        if not path.exists():
            issues.append(
                BatchValidationDocumentResult(
                    input_path=str(path),
                    status=ValidationStatus.failed,
                    message="Input path does not exist.",
                )
            )
            continue

        if path.is_dir():
            discovered.extend(sorted(child for child in path.glob("*.docx") if child.is_file()))
            continue

        if path.suffix.lower() != ".docx":
            issues.append(
                BatchValidationDocumentResult(
                    input_path=str(path),
                    status=ValidationStatus.warning,
                    message="Skipped non-DOCX input path.",
                )
            )
            continue

        discovered.append(path)

    if input_dir is not None:
        directory = Path(input_dir)
        if not directory.exists() or not directory.is_dir():
            issues.append(
                BatchValidationDocumentResult(
                    input_path=str(directory),
                    status=ValidationStatus.failed,
                    message="Input directory does not exist or is not a directory.",
                )
            )
        else:
            discovered.extend(sorted(child for child in directory.glob("*.docx") if child.is_file()))

    unique_discovered = sorted({path.resolve() for path in discovered})
    return unique_discovered, issues


def build_batch_validation_report(
    inputs: list[str] | None = None,
    *,
    input_dir: str | Path | None = None,
    registry_path: str | Path,
    reports_dir: str | Path,
) -> BatchValidationReport:
    discovered, issues = discover_docx_inputs(inputs, input_dir=input_dir)
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    document_results = list(issues)
    for path in discovered:
        output_path = reports_dir / f"{path.stem}.validation_report.json"
        try:
            report = validate_docx_file(input_path=path, registry_path=registry_path)
            output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            document_results.append(
                BatchValidationDocumentResult(
                    input_path=str(path),
                    report_path=str(output_path),
                    report=report,
                    status=ValidationStatus.passed if report.downstream_ready else ValidationStatus.failed,
                    message="Validation report generated." if report.downstream_ready else "Validation report generated with failed checks.",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive batch wrapper
            document_results.append(
                BatchValidationDocumentResult(
                    input_path=str(path),
                    report_path=str(output_path),
                    status=ValidationStatus.failed,
                    message=f"Validation run failed: {type(exc).__name__}: {exc}",
                )
            )

    if not discovered and not issues:
        document_results.append(
            BatchValidationDocumentResult(
                input_path="",
                status=ValidationStatus.warning,
                message="No DOCX inputs were discovered for batch validation.",
            )
        )

    summary = aggregate_batch_results(document_results)
    normalized_inputs = [str(Path(item)) for item in inputs or []]
    if input_dir is not None:
        normalized_inputs.append(str(Path(input_dir)))
    return BatchValidationReport(input_paths=normalized_inputs, documents=document_results, summary=summary)


def aggregate_batch_results(documents: list[BatchValidationDocumentResult]) -> BatchValidationSummary:
    failed_checks: Counter[str] = Counter()
    warning_checks: Counter[str] = Counter()
    passed_documents = 0
    failed_documents = 0
    warnings_count = 0

    for document in documents:
        if document.report is not None:
            if document.report.downstream_ready:
                passed_documents += 1
            else:
                failed_documents += 1
            for check in document.report.checks:
                if check.status == ValidationStatus.failed:
                    failed_checks[check.name] += 1
                elif check.status == ValidationStatus.warning:
                    warning_checks[check.name] += 1
                    warnings_count += 1
            continue

        if document.status == ValidationStatus.failed:
            failed_documents += 1
        elif document.status == ValidationStatus.warning:
            warnings_count += 1
            warning_checks["input_discovery"] += 1

    return BatchValidationSummary(
        total_documents=len(documents),
        passed_documents=passed_documents,
        failed_documents=failed_documents,
        warnings_count=warnings_count,
        common_failed_checks=dict(sorted(failed_checks.items())),
        common_warning_checks=dict(sorted(warning_checks.items())),
    )
