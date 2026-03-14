# Repository Instructions

## Scope
This repository is currently a FastAPI-first TCM study project centered on formula learning.

Current reality:

- backend is implemented
- frontend is not yet in this repository
- formula learning is the active subject model
- OCR, card generation, quiz, and review flows are the critical product path

Future direction to preserve during reviews:

- keep one product/app, not separate apps per subject
- keep shared entities generic
- add subject-specific adapters instead of overloading one schema with all fields

## Architecture Guardrails
- Shared/core entities should remain generic: `Subject`, `Collection`, `SourceDocument`, `KnowledgeCard`, `Quiz`, `ReviewRecord`.
- Subject-specific content should live in dedicated models, schemas, prompts, and services.
- Formula fields must not become implicit requirements for future acupuncture or warm-disease support.
- Shared import, quiz, and review logic should stay separate from subject extraction logic.

## Review Priorities
When reviewing code, prioritize findings in this order:

1. correctness bugs and broken API behavior
2. edge cases around missing collections, documents, or cards
3. schema drift between models, Pydantic responses, and API docs
4. OCR/import and card-generation regressions
5. quiz/review persistence bugs
6. unsafe file handling or temp-file assumptions
7. test gaps in critical flows

## Working Rules
- Prefer the smallest safe patch.
- Do not refactor unrelated files during bug-fix or review tasks.
- Keep route handlers thin and push business logic into services.
- If an endpoint can fail because a record is missing, prefer explicit HTTP-friendly handling over raw framework exceptions.
- Preserve the current backend structure unless the task explicitly asks for larger reorganization.

## Testing Rules
- Start with focused tests for the touched API or service, then expand only if needed.
- Critical flows in this repo are:
  - `GET /health`
  - `POST /api/import/text`
  - `POST /api/import/image`
  - `POST /api/cards/generate`
  - `GET /api/cards`
  - `POST /api/comparisons/generate`
  - `POST /api/quizzes/generate`
  - `POST /api/reviews/submit`
- If adding tests, prefer API-level coverage for contract behavior and service-level coverage for branch-heavy logic.

## Local Command Notes
This repo uses `uv`. In constrained environments, prefer:

```bash
UV_CACHE_DIR=/tmp/uv-cache-ocdoctor PYTHONPATH=backend/src uv run pytest -q
```

If test discovery is adjusted later, keep the command aligned with `pyproject.toml`.
