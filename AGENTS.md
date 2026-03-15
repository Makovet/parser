# AGENTS.md

## Project
This repository contains a DOCX-only template-aware parser for QMS / SMK documents.
Current template target: ADM-TEM-011_B.

## Working style
- Work in small, controlled steps.
- Do not refactor unrelated files.
- Do not redesign the architecture unless explicitly asked.
- Preserve existing project structure and naming.
- Prefer minimal, readable changes over broad rewrites.
- Keep compatibility with existing imports unless explicitly told otherwise.

## Architecture constraints
- Parser is DOCX-only.
- Keep parser layers separated:
  - loading / extraction
  - classification
  - tracking
  - parsing of composite objects
  - pipeline integration
- Do not mix parser responsibilities into one giant module.

## Code constraints
- Python 3.11+
- Use existing Pydantic models where possible.
- Reuse existing style registry and parser output models.
- Avoid adding dependencies unless necessary.
- Keep functions focused and testable.

## Testing
- Run relevant tests after changes.
- If tests are missing for the feature, add minimal tests.
- Do not claim success without reporting test results.

## Required final response format
At the end of each task, always return:

1. Files changed
2. Concise summary of what was implemented
3. Test commands run
4. Test results
5. Assumptions
6. Known limitations
7. Stop here and wait for the next instruction

## Change discipline
- Stop after completing the requested task.
- Do not continue with “helpful extra improvements”.
- Do not modify unrelated modules.
- If something important is unclear, state the assumption explicitly in the final response.