# UX/UI & Accessibility Review

## Context
The GUI has gained responsive layout helpers and theming palettes, yet critical
feedback mechanisms and accessibility affordances still trail expectations for a
productivity desktop tool.

## Findings

### S1 — Progress indicator misleads users
- **Evidence**: The processor increments the `total_files` denominator alongside
  each processed file, so the first callback reports `processed == total`. The
  GUI immediately renders 100% progress and “Processing: 1/1 files.”【F:processor.py†L298-L319】【F:ui.py†L572-L600】
- **Impact**: Operators lose confidence during long runs because the UI appears
  finished even while work continues.
- **Recommendation**: Switch the bar to indeterminate mode until a real total is
  known, or compute counts upfront and emit monotonically increasing progress.

### S2 — Keyboard navigation lacks affordances
- **Evidence**: No accelerators/mnemonics are defined and focus order simply
  follows widget creation; there are no textual hints about shortcuts.【F:ui.py†L136-L332】
- **Impact**: Power users and accessibility customers must tab through long
  chains and cannot trigger core actions (Start, Cancel, Generate Report) via the
  keyboard.
- **Recommendation**: Provide Alt-based mnemonics, document shortcuts within the
  UI (status bar/tooltips), and group related controls to shorten tab cycles.

### S3 — Status messaging lacks contextual guidance
- **Evidence**: Queue log messages append raw strings into the transcript, and
  cancellation success/failure is communicated only through terse text updates.【F:ui.py†L602-L653】
- **Impact**: Users must parse verbose logs to understand what happened; there is
  no inline guidance or links to reports/help.
- **Recommendation**: Introduce structured status panels (success/error banners,
  actionable next steps) and reserve the transcript for detailed logs.

## Open Questions
- **Missing**: Accessibility testing notes (screen reader/keyboard walkthroughs)
  to validate compliance.
- **Missing**: Product requirements for assistive technology support (e.g., high
  contrast tokens, tooltip timing guidelines).
