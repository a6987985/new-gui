# New-GUI Maintenance Boundaries

## Purpose
This note defines the stable maintenance boundaries after the multi-file split.
Use it as the default rule set for future iterations.

Current state:
- `new_gui/reproduce_ui.py` is about 953 lines
- structural split target has been reached
- future work should optimize for stability, not for smaller file count

## Core Rule
Do not keep splitting just to reduce line count.
Only move code when the move improves ownership, clarity, or safety.

## Stable Ownership

### `new_gui/reproduce_ui.py`
Keep these here:
- application entrypoint
- `MainWindow` class
- object lifetime management
- startup sequence
- signal connection entrypoints
- tiny wrappers that preserve existing method names
- timing-sensitive runtime glue

Do not aggressively move:
- watcher and timer wiring
- startup object creation order
- thin wrappers already referenced by signals, menus, or internal callbacks

### `new_gui/ui/builders/`
Own:
- widget creation
- layout tree construction
- setup-time style application
- startup wiring that is purely structural

Rule:
- preserve widget creation order
- preserve layout insertion order
- preserve stylesheet text unless a UI change is intended

### `new_gui/ui/controllers/`
Own:
- UI orchestration
- action flow coordination
- view-mode switching
- menu construction
- theme application

Rule:
- controllers may coordinate multiple UI helpers
- controllers should not become data parsing layers
- controllers should receive `window` and operate on existing runtime state

### `new_gui/services/`
Own:
- run scanning
- dependency parsing
- status/timing lookup
- tune and bsub file operations
- tree-row data shaping
- view snapshot and tree-state helpers

Rule:
- prefer Qt-light helpers here
- keep widget ownership out of services
- keep reusable logic here when it does not require direct window orchestration

### `new_gui/ui/widgets/` and `new_gui/ui/dialogs/`
Own:
- self-contained reusable Qt classes
- local rendering behavior
- local interaction details that do not need `MainWindow` orchestration

## Boundaries We Should Hold

### Do Not Split Further For Now
- `MainWindow` startup and lifecycle root
- watcher and debounce flow
- tree row bridge methods between run data and `QStandardItemModel`
- `top_panel_builder.init_top_panel`
- `services/view_state.py`
- `services/run_repository.py` as the compatibility facade

Reason:
- these areas are already at a good balance of clarity and stability
- further splitting would mostly add indirection and raise regression risk

### Safe To Extend In Place
- add new menu actions inside the current context-menu controller structure
- add new execute/file/tune actions inside `action_controller`
- add new view modes inside `view_controller`
- add new run parsing helpers inside the `services/run_*` modules

## Change Routing Rules

When adding or changing behavior, use this decision path:

1. If the change creates or lays out widgets, place it in `ui/builders/`.
2. If the change coordinates existing UI behavior across methods, place it in `ui/controllers/`.
3. If the change parses files, computes state, or reshapes data, place it in `services/`.
4. If the change is a reusable Qt class, place it in `ui/widgets/` or `ui/dialogs/`.
5. If the change is only a signal-facing wrapper or lifecycle hook, keep it in `reproduce_ui.py`.

## Compatibility Rules

For future refactors:
- keep `MainWindow` method names stable when they are used by signals, menus, shortcuts, or controllers
- do not change widget object names casually
- do not rewrite stylesheet strings unless the UI result is intentionally changing
- do not move code across layers if it introduces circular imports
- prefer moving method bodies first and refactoring behavior later

## Regression Expectations

Any medium- or high-risk change should be checked against:
- main view rendering
- run switching
- search and filter behavior
- status view and trace view
- tune create/copy flow
- file open actions
- context menu actions
- status watcher refresh behavior
- theme and XMETA background rendering

## Practical Stop Rule
Treat the current structure as the default steady-state architecture.
Do not split below the current boundary unless one of these is true:
- a module becomes hard to reason about
- a feature cannot be added cleanly within its current owner
- a reusable piece is clearly being duplicated

If none of the above is true, keep the code where it is.
