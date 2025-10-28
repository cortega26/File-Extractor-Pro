# UX/UI & Accessibility Review

## Context
File Extractor Pro ships as a fixed-size Tkinter desktop interface. The UI is composed entirely inside `FileExtractorGUI.setup_*` methods and lacks a formal design system or token library.

## Findings

### S1 — Fixed layout harms accessibility and responsiveness
- **Evidence**: Window geometry hard-coded to 700×700, with minimum size locked to the same dimensions.【F:file_extractor.py†L333-L350】 Grid rows/columns rarely receive weight, so resizing doesn’t adapt content.
- **Impact**: Users on small screens (e.g., 13" laptops, accessibility zoom) cannot resize below 700px; high-DPI scaling relies on Windows-only DPI tweak. Keyboard/screen-reader users face scroll pain.
- **Recommendation**: Allow dynamic resizing (remove hard min size, configure grid weights). Adopt responsive layout primitives and test with zoom ≥200%.

### S1 — Inadequate theme contrast and no WCAG verification
- **Evidence**: Dark mode sets `background='#2d2d2d'` and `foreground='#ffffff'`, while light mode uses `#f0f0f0`/`#000000` without checking component-level contrast.【F:file_extractor.py†L482-L545】 There is no alt text or accessible descriptions for key controls.
- **Impact**: Potential WCAG 2.1 AA violations (e.g., grey text on grey backgrounds). Users with low vision have no guarantee of sufficient contrast or theme persistence.
- **Recommendation**: Establish color tokens validated against WCAG AA (contrast ≥4.5:1). Provide accessible names via `ttk.Label`/`textvariable` and consider OS theme detection.

### S2 — Keyboard navigation gaps and missing focus feedback
- **Evidence**: Many widgets (e.g., `ttk.Checkbutton` for extensions) are added without explicit focus order or accelerator keys.【F:file_extractor.py†L364-L451】 No focus highlight customization.
- **Impact**: Users relying on keyboard navigation may struggle to jump between sections; no instructions indicate hotkeys beyond hidden `<F5>` binding.
- **Recommendation**: Define mnemonic/accelerators (e.g., Alt+ key). Add status text describing `<F5>`/`Esc`. Ensure focus rectangles remain visible under both themes.

### S2 — Sparse feedback for long-running operations
- **Evidence**: Progress bar increments only on processed files; there is no skeleton/loading placeholder in the output pane while queued logs accumulate.【F:file_extractor.py†L560-L667】
- **Impact**: Perceived idleness on large operations; cancellations rely on queue messages.
- **Recommendation**: Introduce explicit “working…” state, disable secondary actions, and show estimated remaining time once metrics exist.

### S3 — Missing empty/error states polish
- **Evidence**: When no extraction data exists, app pops a modal but leaves the output area blank.【F:file_extractor.py†L676-L714】 Error dialogs reuse generic messages.
- **Impact**: Users cannot recover easily or learn next steps.
- **Recommendation**: Add inline empty states (illustrative text) and actionable error messages (e.g., “Check permissions on …”).

## Open Questions
- **Missing**: Design system or Figma references to align tokens.
- **Missing**: Accessibility testing notes (screen reader, keyboard walkthroughs) to validate compliance.
