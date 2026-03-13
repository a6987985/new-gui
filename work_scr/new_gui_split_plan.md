# New-GUI Multi-File Split Plan

## 1. Goal

This document records the real split progress for `new_gui/reproduce_ui.py`.

The goals remain unchanged:

- keep all existing features unchanged
- keep all visual structure unchanged
- keep all styles unchanged
- reduce the size and coupling of `new_gui/reproduce_ui.py`
- preserve `new_gui/reproduce_ui.py` as the runtime entry

This is a structural refactor, not a redesign.

## 2. Non-Negotiable Rules

These rules remain active:

- Do not change widget hierarchy, layout order, spacing, or geometry logic.
- Do not change stylesheet strings, colors, font sizes, paddings, or borders unless moved without modification.
- Do not change signal-slot behavior.
- Do not rename public behavior that is already used by shortcuts, actions, menu items, or delegates.
- Move code first, refactor architecture second.
- Keep MainWindow orchestration in `new_gui/reproduce_ui.py` unless there is a very strong reason to move it.

## 3. Actual Current Structure

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

## 4. Progress Snapshot

### 4.1 Completed

#### Static extraction

Completed:

- `config/settings.py`
- `ui/theme_runtime.py`
- `ui/widgets/labels.py`
- `ui/widgets/scrollbars.py`
- `ui/widgets/filter_header.py`
- `ui/widgets/delegates.py`
- `ui/widgets/status_bar.py`

#### Dialog extraction

Completed:

- `ui/dialogs/params_editor.py`
- `ui/dialogs/dependency_graph.py`
- `ui/dialogs/tune_dialogs.py`

#### File/data services

Completed:

- dependency parsing
- tune file discovery
- tune candidate parsing
- bsub parameter read/write
- run scanning
- status cache building
- time cache building
- all-status overview data
- dependency graph data
- retrace target lookup
- tune create/copy helpers
- file open/path helpers
- shell action helpers

#### High-risk tree/view split

Completed in service layers:

- `tree_rows.py`
  - standard headers
  - row construction
  - row refresh
- `tree_structure.py`
  - grouped level/target structure
  - search grouping
  - status grouping
- `view_state.py`
  - snapshot capture/restore
  - target selection helpers
  - trace visibility reset
- `view_restore.py`
  - restore-plan build/apply
- `view_modes.py`
  - active view mode classification
- `run_views.py`
  - all-status row construction
  - selected run activation helpers
- `search_flow.py`
  - search context capture
  - refresh restoration
  - exit-search restoration
- `status_summary.py`
  - full-run statistics computation
- `tree_editing.py`
  - editable tree cell parsing and validation
- `view_tabs.py`
  - Main / Status / Trace / All Status tab presentation states

#### Dead code cleanup

Completed after reachability analysis:

- removed `get_tree`
- removed `get_target`
- removed `tar_name`
- removed `search_selected_targets`
- removed `_run_target_cache_key`
- removed `_serialize_tree_row`
- removed `has_tune`
- removed the unused `MainWindow.show_all_children()` wrapper

### 4.2 Not Completed Yet

These are the remaining optional tasks, not blockers for current runtime stability.

#### Optional service-internal cleanup

Still possible:

- split `run_repository.py` into smaller service files
  - dependency helpers
  - status/time cache helpers
  - tune/bsub helpers
  - overview/graph helpers

#### Optional documentation cleanup

Still possible:

- keep architecture docs synchronized with the current package layout
- remove stale references from older notes if more are found later

#### Optional smoke automation

Still possible:

- add repeatable import smoke checks
- add service-level regression scripts
- add optional offscreen Qt smoke coverage for tree/view helpers

## 5. Final Recommended Boundary

The project is now near the correct stop point for this refactor.

### Keep in `new_gui/reproduce_ui.py`

These should remain as orchestration logic:

- `MainWindow.__init__`
- `_init_menu_bar`
- `_init_central_widget`
- `_init_top_panel`
- keyboard shortcut wiring
- menu wiring
- `populate_data`
- `close_tree_view`
- `retrace_tab`
- `show_context_menu`
- watcher/timer wiring

### Keep as-is for stability

These custom Qt behavior islands are not good candidates for further aggressive splitting:

- `ColorTreeView.drawBranches`
- `RoundedScrollBar`
- custom delegate paint logic
- `BoundedComboBox`
- notification widgets/managers

### Why this is the stop point

At this stage the remaining large pieces are mostly Qt orchestration, not pure business logic.
Further splitting would mostly move fragile widget state around and increase regression risk.

## 6. What Was Intentionally Not Done

The following originally imagined targets were not created, on purpose:

- `ui/widgets/tree_view.py`
- `ui/widgets/combo_box.py`
- `ui/notifications.py`
- `services/target_actions.py`
- `services/tree_filters.py`
- `services/menu_builder.py`
- `app/main_window.py`

Reason:

- those boundaries looked clean on paper
- but in the real code they would have required more aggressive orchestration moves
- that would have increased the risk of behavior drift

The actual split follows runtime coupling, not idealized folder symmetry.

## 7. Regression Checklist

The current split is considered acceptable only if these continue to pass:

- application starts without import errors
- run selector loads and switches correctly
- tree view columns, widths, and colors remain unchanged
- search still filters correctly
- trace up/down still works
- status badge filtering still works
- tab close still returns to Main View correctly
- all-status overview still works
- tune creation/open/copy still works
- bsub edit still works
- params dialogs still open and save correctly
- dependency graph still opens
- footer status badges and statistics still render correctly
- custom scrollbar style still appears correctly

## 8. Execution Recommendation

For the current codebase, the recommended next order is:

1. inner-network regression using the latest multi-file bundle
2. optional split of `run_repository.py` only
3. stop structural refactor work after that unless a new problem appears

## 9. Current Conclusion

This split is no longer in early planning.
It is in late-stage stabilization.

That means:

- the architecture is already mostly in place
- the priority is now regression safety, not more aggressive decomposition
- any further refactor should be justified by a real maintenance or testing need
