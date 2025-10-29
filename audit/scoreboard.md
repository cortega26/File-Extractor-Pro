# Delivery Scoreboard

This scoreboard tracks progress against the audit backlog so future contributors
can quickly see what has been addressed and what remains.

## Legend
- **Status** — `Not Started`, `In Progress`, `Done`, or `Blocked`.
- **Next Action** — concrete step to move the item forward.

## Must Have (Severity S0–S1)
- **Q-101 (S1 · CLI)** — Status: *Not Started*
  - Notes: Headless workflow defaults to an empty extension list, so no files are processed unless the operator opts in manually.
  - Next Action: Update CLI parsing to expand missing extensions to `COMMON_EXTENSIONS` (or wildcard) and add regression coverage.
- **Q-102 (S1 · UX/Feedback)** — Status: *Not Started*
  - Notes: Progress denominator increases with each processed file, forcing the progress bar to show 100% almost immediately.
  - Next Action: Provide an upfront count (dry run/estimation) and switch to determinate progress only when the total is known.
- **Q-103 (S1 · Maintainability)** — Status: *Not Started*
  - Notes: `ui.py` remains a ~1k-line monolith blending layout, state, theming, and service calls.
  - Next Action: Extract presenter/controller modules and introduce widget factories with targeted unit tests.
- **Q-104 (S1 · Tooling)** — Status: *Not Started*
  - Notes: `mypy --strict .` reports 62 failures across services, UI, and tests.
  - Next Action: Add missing annotations/stubs and configure strictness tiers so type checking can gate CI.

## Should Have (Severity S2)
- **Q-105 (S2 · Performance)** — Status: *Not Started*
  - Notes: Files over 100 MB raise `MemoryError`, leaving large assets unprocessed.
  - Next Action: Replace the static cap with a streamed guard tied to configuration/available memory.
- **Q-106 (S2 · Concurrency)** — Status: *Not Started*
  - Notes: Queue backpressure evicts arbitrary messages, risking dropped terminal state updates.
  - Next Action: Introduce batch draining or separate channels for state vs. log messages.
- **Q-107 (S2 · Accessibility)** — Status: *Not Started*
  - Notes: No mnemonics or shortcut hints exist; tab order follows raw widget creation.
  - Next Action: Define Alt-based accelerators and document keyboard workflows within the UI.
- **Q-108 (S2 · Observability)** — Status: *Not Started*
  - Notes: No instrumentation for throughput, elapsed time, or queue saturation.
  - Next Action: Emit structured run summaries (logs/metrics) after each extraction.

## Nice to Have (Severity S3)
- **Q-109 (S3 · Documentation)** — Status: *Not Started*
  - Notes: README lacks CLI usage guidance, so operators miss the need for `--extensions`.
  - Next Action: Add CLI section detailing defaults, required flags, and examples.
- **Q-110 (S3 · Testing)** — Status: *Not Started*
  - Notes: Coverage tooling/thresholds are absent despite R3 requirements.
  - Next Action: Wire `pytest-cov` (or coverage.py) into CI with ≥80% overall, ≥90% for changed modules.

## Recently Completed
- _None — new findings identified during this audit._
