# Code Quality & Architecture Report

## Overview
File Extractor Pro is currently implemented as a single Tkinter desktop application. All GUI wiring, configuration, and asynchronous file traversal live inside `file_extractor.py`, which now spans more than 800 lines and mixes UI logic, filesystem I/O, and concurrency primitives. The code base lacks automated tests and modular boundaries, which raises maintenance and scalability concerns for future iterations (e.g., adding CLIs or headless processing).

## Findings

### S1 — Monolithic module coupling GUI, config, and I/O
- **Evidence**: `file_extractor.py` defines configuration helpers (`Config`), async extraction (`FileProcessor`), and Tk UI (`FileExtractorGUI`) in one file, with the GUI directly instantiating and controlling asynchronous extraction threads.【F:file_extractor.py†L48-L828】
- **Impact**: Hard to reason about or unit-test individual concerns; any change to extraction requires touching GUI code. Scaling to alternative front-ends or a service workflow would require major rewrites. Bugs in one area (e.g., async) can crash the GUI.
- **Recommendation**: Split into packages: `config.py`, `processors/async_extractor.py`, `ui/main_window.py`. Define explicit interfaces for the processor and use dependency injection so GUI and batch modes share logic. Add unit tests around the processor module once isolated.

### S1 — Async event loop misuse with Tkinter thread
- **Evidence**: `run_extraction_thread` spins up `asyncio.new_event_loop()` inside a worker thread and calls `loop.run_until_complete`, while `update_progress` schedules Tk updates back on the main thread.【F:file_extractor.py†L604-L655】 Tkinter is not designed to cooperate with asyncio without integrating the loop; cancellation and shutdown rely on thread-level flags only.
- **Impact**: Risk of deadlocks or crashes when cancelling extractions; Windows event loop policy may reject nested loops. Hard to extend for multiple concurrent tasks or progress callbacks. Observed that `self.loop` is stored but never awaited for cancellation.
- **Recommendation**: Replace with `asyncio`-aware orchestration (e.g., `asyncio.run` in background worker with thread-safe queues) or drop asyncio in favor of thread pool + synchronous file reads. Provide explicit cancellation hooks that close the loop gracefully.

### S2 — Duplicate directory walks and unbounded queue writes
- **Evidence**: `extract_files` performs two full `os.walk` passes: first to count eligible files, second to process them, repeating filtering logic and doubling filesystem I/O.【F:file_extractor.py†L214-L313】 Messages are enqueued via `self.output_queue.put` without bounded size, risking memory growth on large runs.【F:file_extractor.py†L122-L184】【F:file_extractor.py†L630-L667】
- **Impact**: On large trees, runtime roughly doubles. The GUI thread may lag if the queue floods faster than `check_queue` drains.
- **Recommendation**: Collapse into a single traversal that counts and processes in one pass while tracking totals. Consider `queue.SimpleQueue` or bounding queue size with backpressure.

### S2 — Configuration persistence lacks schema validation
- **Evidence**: `Config.set` writes arbitrary values as strings without validation; `set_defaults` stores comma-separated lists, but `get` doesn’t coerce types, so booleans like `include_hidden` depend on `.lower() == 'true'` callers.【F:file_extractor.py†L66-L149】【F:file_extractor.py†L357-L417】
- **Impact**: Invalid values in `config.ini` can silently propagate (e.g., `mode=foobar`), causing runtime errors later. Hard to introduce new settings safely.
- **Recommendation**: Introduce a schema (pydantic/dataclasses) with validation and typed getters; store structured lists in JSON fields to avoid fragile CSV parsing.

### S2 — Lack of error domain separation and retry strategy
- **Evidence**: Errors in `process_file` surface to the GUI via queue messages, but operations like `aiofiles.open` and `os.walk` exceptions bubble into a single generic `"Error during extraction"` handler.【F:file_extractor.py†L122-L313】
- **Impact**: Users cannot distinguish between transient permission errors and fatal crashes. No retries for transient I/O, no partial failure reporting for long runs.
- **Recommendation**: Introduce domain-specific exceptions (`FileTooLarge`, `PermissionDenied`). Log structured error events and surface actionable messages, optionally with a retry/resume workflow.

### S3 — Logging handler instantiated at import time
- **Evidence**: Rotating file handler configured globally when module imports.【F:file_extractor.py†L38-L55】
- **Impact**: Importing the module in tests or alternate front-ends always mutates logging, breaking embedding scenarios. Hard to adjust log path per environment.
- **Recommendation**: Move logging setup into `main()` or a dedicated `configure_logging()` function guarded by `if __name__ == "__main__"` and allow dependency injection.

## Opportunities
- Introduce a thin service layer that orchestrates extraction requests, enabling CLI/daemon reuse.
- Create DTOs for extraction reports to enforce schema compatibility.
- Add metrics instrumentation (timings, counts) to support performance tuning.

## Open Questions
- **Missing**: Architecture decision records or roadmap—needed to prioritize refactors.
- **Missing**: Clarification whether headless/batch mode is a requirement; influences modularization approach.
