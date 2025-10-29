# Performance & Web Vitals Summary

## Current State
- Desktop Tkinter app; Lighthouse/Web Vitals are not applicable, so perceived
  responsiveness focuses on queue throughput and progress accuracy.
- Processor streams file contents chunk-by-chunk and shares a bounded queue with
  the UI/CLI for status updates.

## Key Findings

### S1 — Progress UI reports 100% almost immediately
- **Evidence**: `FileProcessor.extract_files` increments `total_files` as each
  file is processed, so the first `progress_callback` invocation receives
  identical numerator/denominator values.【F:processor.py†L298-L319】 `update_progress`
  converts that into a 100% progress reading.【F:ui.py†L572-L600】
- **Impact**: Users lose trust in progress feedback, making long-running
  extractions feel stalled.
- **Recommendation**: Pre-compute an estimated total (dry run/heuristic) or
  treat progress as indeterminate until the workload is known.

### S2 — Hard 100 MB cap blocks large text assets
- **Evidence**: `process_file` raises `MemoryError` when `file_size > 100 * 1024 *
  1024` despite streaming content to the destination handle.【F:processor.py†L83-L139】
- **Impact**: Large logs or SQL dumps fail silently (error message only), slowing
  scripted workflows that depend on complete extraction.
- **Recommendation**: Replace the static guard with a configurable threshold or a
  streaming watchdog tied to available memory, and surface clearer telemetry when
  a file is skipped.

### S2 — Queue backpressure risks losing completion signals
- **Evidence**: When the queue is full, `_enqueue_message` dequeues the oldest
  item without checking type, then may still drop the new message if the queue
  remains saturated.【F:processor.py†L24-L50】
- **Impact**: CLI automation may never observe the terminal state payload,
  forcing longer polling loops and degrading responsiveness.
- **Recommendation**: Batch-drain the queue on the producer side or prioritise
  state messages via a separate channel.

### S3 — No telemetry for throughput or queue saturation
- **Evidence**: Neither the processor nor service captures elapsed time, file
  throughput, or queue depth.
- **Impact**: Performance regressions go unnoticed and there is no baseline for
  tuning polling intervals.
- **Recommendation**: Emit per-run metrics (elapsed time, files/sec, max queue
  depth) at INFO level and consider exporting them for future web/API surfaces.

## Suggested Optimisation Plan
1. Fix the progress denominator and add tests that assert monotonic progress.
2. Make the large-file guard configurable and document recommended values per
   environment.
3. Revisit queue backpressure with batch draining and prioritised state events.
4. Instrument extraction runs with timing/queue metrics and feed them into CI
   regression dashboards.

## Open Questions
- **Missing**: Target data sizes (number of files, expected max file size) to
  calibrate heuristics.
- **Missing**: Performance budgets for future CLI/API consumers (e.g., expected
  P95 runtime for 10 k files).
