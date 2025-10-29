## Overview
File Extractor Pro now splits responsibilities across dedicated modules:
`processor.py` owns filesystem traversal, `services/` provides orchestration
primitives for the GUI and CLI, and `ui.py` drives the Tkinter surface. The
separation is a marked improvement over the prior monolith, yet several
architectural gaps remain. In particular, the headless contract is inconsistent
with the processor’s filtering rules, the GUI module has grown into a
nearly-1 000 line façade, and static analysis is not enforceable because type
information is missing across core modules and tests.

## Findings

### S1 — CLI defaults filter out every file
- **Evidence**: The argument parser keeps inclusion mode as the default while
  leaving `--extensions` empty, so `_split_csv` returns `()` and
  `FileProcessor.extract_files` rejects every candidate file.【F:services/cli.py†L82-L168】【F:processor.py†L298-L319】
- **Impact**: Running `python -m services.cli <folder>` exits successfully but
  produces no output, breaking the core extraction flow for automation owners.
- **Recommendation**: Expand an empty extensions tuple to a sensible default
  (`COMMON_EXTENSIONS`) or treat it as a wildcard. Add integration coverage to
  lock the contract.

### S1 — GUI module remains a monolith
- **Evidence**: `ui.py` spans 972 lines and the `FileExtractorGUI` class still
  handles layout, state management, theming, and service orchestration directly.【F:ui.py†L78-L653】【b0562d†L1-L1】
- **Impact**: Adding features or accessibility hooks forces contributors to
  touch the same giant class, increasing review risk and making unit testing
  difficult.
- **Recommendation**: Introduce presenter/controller layers (e.g., extract
  theme manager, queue consumer, and form builders into separate modules) and
  cover them with focused tests.

### S1 — Type checking cannot gate CI
- **Evidence**: `mypy --strict .` fails with 62 errors across services, UI, and
  tests, citing missing annotations and protocol mismatches.【416f23†L1-L65】
- **Impact**: Without type coverage the team cannot rely on static analysis to
  catch regressions (e.g., signature changes in `ExtractorService`).
- **Recommendation**: Layer in type hints, supply Tk stubs, and configure mypy
  strictness tiers so CI can enforce R3 requirements.

### S2 — Queue backpressure can drop terminal state updates
- **Evidence**: `_enqueue_message` evicts an arbitrary message whenever the
  bounded queue is full, then retries once before dropping the new payload.【F:processor.py†L24-L50】
- **Impact**: During noisy runs the terminal `("state", {"result": …})`
  message can be discarded, leaving the UI/CLI without a completion signal.
- **Recommendation**: Prioritise state events by draining batches before
  enqueueing, or split state and log channels so completion messages are never
  evicted.

### S2 — Large-file safeguard blocks valid workloads
- **Evidence**: `process_file` raises `MemoryError` for files over 100 MB even
  though content is streamed chunk-by-chunk.【F:processor.py†L83-L139】
- **Impact**: Repositories with sizable text assets (logs, SQL dumps) cannot be
  processed despite available disk/memory.
- **Recommendation**: Replace the hard-coded cap with a configurable guard or
  remove it entirely in favour of streamed writes plus documentation.

## Opportunities
- Formalise service interfaces (e.g., a thin domain layer) so new front-ends
  reuse orchestration logic without importing Tk modules.
- Capture extraction summaries through typed DTOs to stabilise report schemas.
- Adopt dependency inversion for logging so tests can inject structured sinks
  without mutating global handlers.

## Open Questions
- **Missing**: Target CLI use cases—should headless runs default to broad
  filters or mirror the GUI defaults?
- **Missing**: Acceptance criteria for large file support (max size, binary vs
  text) to inform guardrail configuration.
