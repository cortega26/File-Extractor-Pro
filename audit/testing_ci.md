# Test Suite & CI Assessment

## Overview
The repository now ships a healthy pytest suite covering the processor,
services, and GUI helpers (29 passing tests, 3 skipped). Linting via Ruff/Black
is configured, but type checking and security tooling are not yet enforceable,
and coverage metrics are absent.

## Findings

### S1 — Strict type checking still fails
- **Evidence**: Running `mypy --strict .` emits 62 errors spanning services, UI,
and tests.【416f23†L1-L65】
- **Impact**: Missing annotations prevent the team from gating merges on type
safety, undermining maintainability guarantees.
- **Recommendation**: Add annotations/stubs and tailor mypy configuration so the
strict run passes in CI.

### S2 — Security scanners missing from toolchain
- **Evidence**: `bandit`, `gitleaks`, and `pip-audit` are not installed, so
  security gates cannot run locally or in CI.【a524bd†L1-L2】【0b1ac2†L1-L2】【a1dc8c†L1-L2】
- **Impact**: High/medium severity findings could slip through without review,
breaching R2 requirements.
- **Recommendation**: Add the tools to `requirements.txt` (or a dev extras) and
wire them into the pipeline with fail-fast behaviour.

### S2 — Coverage targets not enforced
- **Evidence**: Pytest runs without `pytest-cov` or coverage thresholds; no
reporting exists in the repo.
- **Impact**: There is no automated guardrail to maintain ≥80% overall coverage
or 90% on touched modules (R3).
- **Recommendation**: Integrate coverage.py/pytest-cov, publish HTML/XML reports,
and gate merges on configured thresholds.

## Coverage Targets
- Maintain ≥80% line coverage overall and ≥90% for changed modules.
- Ensure branch coverage ≥70% for critical paths (processor/service layers).

## Open Questions
- **Missing**: CI provider details (GitHub Actions, GitLab) to draft pipeline
  templates.
- **Missing**: Historical flake data to prioritise stabilisation work.
