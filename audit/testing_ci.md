# Test Suite & CI Assessment

## Overview
The repository contains no automated tests or CI configuration. Quality gates (lint, type checks, security scans) are absent, leaving regressions undetected until runtime.

## Findings

### S0 — No automated tests for critical extraction flow
- **Evidence**: Repository lacks a `tests/` directory; no unit/integration/E2E coverage. `file_extractor.py` handles extraction, threading, and GUI without safeguards.【F:file_extractor.py†L48-L828】
- **Impact**: Core user flow (select folder → extract → report) can break silently. Refactors cannot be validated without manual QA. Violates R3 coverage targets.
- **Recommendation**: Introduce pytest suite with fixtures mocking filesystem and queues. Aim for ≥90% coverage on extraction logic before further changes.

### S1 — No lint/type/security enforcement
- **Evidence**: No configuration files for Ruff/Black/Isort/Mypy/Bandit/Gitleaks. README lacks CI instructions.
- **Impact**: Style drift, type regressions, and security issues (e.g., path traversal) may slip into releases.
- **Recommendation**: Add pre-commit hooks, CI pipeline running lint, mypy, pytest, bandit, gitleaks, pip-audit. Gate merges on success.

### S2 — Manual config of dependencies risks drift
- **Evidence**: `requirements.txt` lists only `aiofiles` without pin/version constraints or dev dependencies.
- **Impact**: Contributors may use inconsistent tool versions, undermining reproducibility.
- **Recommendation**: Adopt `requirements.in`/`poetry` lockfile or at least pin versions and add dev extras (testing, linting).

## Coverage Targets
- Unit: ≥80% overall, extraction module ≥90% lines, ≥70% branches.
- Integration: Cover folder selection, cancellation, and report generation via headless tests (e.g., `pytest-qt` alternative or CLI harness).
- E2E/manual: Provide checklist for GUI interactions until automation feasible.

## Open Questions
- **Missing**: CI environment (GitHub Actions, GitLab) to define pipeline templates.
- **Missing**: Historical bug data to prioritize regression tests.
