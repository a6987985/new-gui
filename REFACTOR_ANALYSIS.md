# New-GUI Refactor Analysis

> Created: 2026-03-07
> Updated: 2026-03-13
> Status: Multi-file split substantially complete
> Entry: `new_gui/reproduce_ui.py`

## Summary

The original refactor analysis proposed a mixin-based reorganization while keeping a single-file architecture.
That is no longer the active plan.

The actual implementation now uses a package-based split under `new_gui/`, while keeping
`new_gui/reproduce_ui.py` as the application entry and MainWindow orchestration layer.

This document now records the real state of the refactor, the remaining safe work, and the final stop boundary.

## Current State

### Runtime entry

- `python new_gui/reproduce_ui.py`

### Current size snapshot

| Item | Value |
|---|---:|
| `new_gui/reproduce_ui.py` lines | 3215 |
| `MainWindow` methods | 109 |
| `run_repository.py` lines | 580 |
| Service modules | 13 |
| Extracted widget modules | 5 |
| Extracted dialog modules | 3 |

### Current package structure

```text
new_gui/
├── config/
│   └── settings.py
├── ui/
│   ├── theme_runtime.py
│   ├── widgets/
│   │   ├── delegates.py
│   │   ├── filter_header.py
│   │   ├── labels.py
│   │   ├── scrollbars.py
│   │   └── status_bar.py
│   └── dialogs/
│       ├── dependency_graph.py
│       ├── params_editor.py
│       └── tune_dialogs.py
├── services/
│   ├── action_flow.py
│   ├── file_actions.py
│   ├── run_repository.py
│   ├── run_views.py
│   ├── search_flow.py
│   ├── status_summary.py
│   ├── tree_editing.py
│   ├── tree_rows.py
│   ├── tree_structure.py
│   ├── tune_actions.py
│   ├── view_modes.py
│   ├── view_restore.py
│   ├── view_state.py
│   └── view_tabs.py
└── reproduce_ui.py
```

## Completed Work

### 1. Low-risk extraction completed

The following are already moved out of `reproduce_ui.py` and are stable:

- configuration and constants: `config/settings.py`
- theme runtime: `ui/theme_runtime.py`
- reusable widgets:
  - `filter_header.py`
  - `delegates.py`
  - `labels.py`
  - `scrollbars.py`
  - `status_bar.py`
- dialogs:
  - `params_editor.py`
  - `dependency_graph.py`
  - `tune_dialogs.py`

### 2. Data/file services completed

The following logic is already extracted into services and called through MainWindow wrappers or orchestration:

- dependency parsing
- run scanning
- status cache building
- target time cache building
- retrace target lookup
- dependency graph data construction
- tune file discovery
- tune candidate discovery from `cmds/*.cmd`
- bsub parameter read/write
- user/tile/csh/log/cmd file resolution
- tune create/copy helpers
- shell action command construction and execution helpers

### 3. High-risk tree/view split completed in layers

The most sensitive logic has already been decomposed into smaller service layers while keeping the visible behavior unchanged:

- row creation and row refresh: `tree_rows.py`
- tree grouping and filtering data: `tree_structure.py`
- snapshot capture/restore and selection helpers: `view_state.py`
- restore-plan replay: `view_restore.py`
- view mode classification: `view_modes.py`
- all-status run-view helpers: `run_views.py`
- search-state capture and restoration: `search_flow.py`
- status summary calculation: `status_summary.py`
- editable tree cell parsing/validation: `tree_editing.py`
- tab presentation state: `view_tabs.py`

### 4. Dead code cleanup completed

The following were verified as truly unused in the runtime code path and removed:

- `get_tree`
- `get_target`
- `tar_name`
- `search_selected_targets`
- `_run_target_cache_key`
- `_serialize_tree_row`
- `has_tune`
- `show_all_children` wrapper in `MainWindow`

Important note:

- the active recursive implementation of `show_all_children` still exists in `services/view_state.py`
- only the unused wrapper in `MainWindow` was removed

## What Changed From The Original Analysis

The original mixin plan is now obsolete for this project.

Reasons:

- the project no longer follows the single-file-only refactor path
- package extraction has already happened and is working in real inner-network testing
- continuing toward mixins would add a second architectural transition with little benefit

Therefore:

- do not use this document as a mixin migration guide anymore
- use it as a status and boundary record only

## Remaining Safe Work

These are still reasonable if we want more cleanup without increasing regression risk too much.

### Safe to continue

1. Split `run_repository.py` internally
- recommended boundaries:
  - dependency parsing
  - status/time cache helpers
  - tune/bsub helpers
  - overview/graph helpers

2. Clean historical docs and generated analysis notes
- update plan docs
- remove stale references to deleted methods

3. Add more focused smoke checks
- import smoke checks
- pure service behavior checks
- optional Qt offscreen smoke checks for tree/view helpers

## Final Stop Boundary

These areas should now be treated as the practical refactor boundary.

### Do not continue splitting aggressively

1. `MainWindow` UI construction
- `_init_top_panel`
- `_init_central_widget`
- menu and top-button wiring

2. Main orchestration flows
- `populate_data`
- `close_tree_view`
- `retrace_tab`
- `show_context_menu`

3. custom drawing / Qt behavior islands
- `ColorTreeView.drawBranches`
- `RoundedScrollBar`
- delegate painting logic
- notification widgets
- `BoundedComboBox`

### Why this is the boundary

At this point the remaining code inside `MainWindow` is mostly orchestration glue.
Further extraction would mainly move Qt state coupling around instead of reducing real complexity.
That would increase regression risk more than it would improve maintainability.

## Review Conclusion

The current multi-file split is already in a good stopping state.

Recommended direction from here:

- keep `new_gui/reproduce_ui.py` as the stable entry and orchestration layer
- avoid another large architectural pass
- if more cleanup is desired, prefer small service-internal splits and documentation cleanup

## Current Recommendation

If we keep iterating, the best next steps are:

1. inner-network regression verification with the latest bundle
2. optional internal split of `run_repository.py`
3. lightweight automated smoke coverage for the extracted services

Anything beyond that should be treated as a new project phase, not as incremental cleanup.
