# Q-002 Architecture Decoupling Plan

## Objective
Separate the core extraction logic from the Tkinter GUI so that processing can be reused by alternative front ends and automated runners without importing UI modules.

## Current Pain Points
- `ui.FileExtractorGUI` instantiates `Config` and `FileProcessor` directly, mixing presentation with configuration and orchestration.
- Async worker lifecycle (loop/thread) is owned by the GUI, making it difficult to call the processor from non-UI contexts.
- Shared constants are imported from `constants.py`, but stateful behaviours (queues, cancellation) are scattered between `ui.py` and `processor.py`.

## Proposed Architecture
1. **Core Service Layer (`services/extractor_service.py`):**
   - Encapsulate orchestration of `FileProcessor`, background thread/async loop, and status queue management.
   - Provide start/cancel APIs that are UI-agnostic.
   - Accept configuration dataclass describing extraction parameters.
2. **Configuration Layer (`config_manager.py`):**
   - Expose pure validation/loading functions returning typed config objects.
   - Avoid side effects at import; allow dependency injection for config sources.
3. **UI Layer (`ui.py`):**
   - Bind widgets to a `ExtractorController` interface exposing high-level commands.
   - Subscribe to status updates via callbacks provided by the service layer.
4. **Entry Points:**
   - CLI or automated runners can instantiate the same service without Tkinter dependencies.

## Incremental Steps
1. Define configuration dataclasses in `config_manager.py` to represent extractor settings.
2. Extract queue + async runner logic from `FileExtractorGUI` into a new `ExtractorService` that lives outside Tkinter.
3. Update `FileProcessor` to accept dependency-injected callbacks instead of directly touching Tkinter state.
4. Refactor `ui.py` to consume the new service, keeping only presentation logic in Tkinter.
5. Introduce unit tests covering the service layer to ensure GUI-free execution path.

## Immediate Next Action
Create the `services` package with an initial `extractor_service.py` skeleton and migrate queue/loop management out of the GUI class.

## Risks & Considerations
- Ensure thread/async lifecycle remains compatible with Tkinter main loop.
- Maintain backwards compatibility for existing CLI/GUI entry points.
- Update documentation (README, user guide) once the service layer stabilises.
