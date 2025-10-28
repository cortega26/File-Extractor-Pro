# Performance & Web Vitals Summary

## Current State
- Desktop Tkinter app; no web routes to measure Lighthouse. Performance concerns relate to filesystem throughput and GUI responsiveness.
- No automated profiling or telemetry exists. Progress updates rely on queue polling every 100 ms, and extraction runs entirely on a background thread executing async file I/O.

## Key Findings

### S1 — Inefficient double traversal inflates runtime
- **Evidence**: `FileProcessor.extract_files` walks the directory tree twice (once to count files, once to process) applying identical filters each time.【F:file_extractor.py†L214-L313】
- **Impact**: Large projects suffer ~2× disk I/O and slower completion, hurting perceived responsiveness and delaying progress updates.
- **Recommendation**: Merge counting and processing into a single traversal, accumulating totals as files are processed. Cache compiled patterns for filters to avoid repeated `fnmatch` evaluation.

### S2 — Progress updates limited by Tk polling cadence
- **Evidence**: GUI schedules `check_queue` every 100 ms and uses `after(0, …)` for progress updates.【F:file_extractor.py†L616-L668】
- **Impact**: On fast SSDs, the queue can fill faster than it drains, causing lag. Users may see stale progress percentages, undermining trust.
- **Recommendation**: Increase queue drain frequency (e.g., `after(10, …)`), or process messages in batches using `queue.SimpleQueue`. Consider streaming progress via `asyncio` callbacks tied to file batches.

### S2 — Missing backpressure on large files
- **Evidence**: `process_file` reads entire file content into memory (`content.append` + join).【F:file_extractor.py†L154-L205】 Files up to 100 MB are allowed before raising `MemoryError`.
- **Impact**: Large but below-threshold files can spike memory usage, affecting system responsiveness.
- **Recommendation**: Stream chunks directly to output rather than buffering, or raise the threshold logic to chunk-write.

### S3 — No timing or Web Vitals instrumentation
- **Evidence**: No timers/logging for per-file durations or queue latency.
- **Impact**: Hard to benchmark improvements or detect regressions.
- **Recommendation**: Record metrics (start/end timestamps, files/sec, queue depth). For future web delivery, establish Web Vitals budgets (LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1) even if not yet applicable.

## Suggested Optimization Plan
1. Refactor extractor to single-pass streaming; measure files/sec before/after.
2. Introduce metrics hooks (e.g., `time.perf_counter`) to log run summaries.
3. Stress-test with >10k files; adjust queue polling to maintain <50 ms latency.
4. Document target budgets for future web port or API responses (e.g., API <300 ms P95 for metadata listing).

## Open Questions
- **Missing**: Production hardware profile; impacts queue tuning.
- **Missing**: Target dataset sizes (number of files, average size) to define realistic budgets.
