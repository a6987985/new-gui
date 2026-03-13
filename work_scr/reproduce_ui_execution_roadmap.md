# reproduce_ui.py Execution Roadmap

## Objective
Drive `new_gui/reproduce_ui.py` from about 3215 lines toward about 950-1150 lines without changing:
- runtime behavior
- widget structure
- layout order
- signal-slot semantics
- stylesheet results
- refresh timing

## Working Rule
This roadmap is implementation-first and refactor-later.
For every slice:
1. move code bodies out first
2. keep `MainWindow` method names stable
3. keep signal connection points in `MainWindow`
4. keep startup entry in `reproduce_ui.py`
5. compile after each slice
6. do inner-network regression after each medium/high-risk slice

## Baseline
- original `new_gui/reproduce_ui.py`: about 3215 lines
- current `new_gui/reproduce_ui.py`: about 953 lines after Slice 1, Slice 2, Slice 3, Slice 4, and Slice 5
- Current target after full roadmap: about 950-1150 lines

## Slice 1
Status: completed
Goal: move remaining in-file custom widget classes out of `reproduce_ui.py`

### Create
- `new_gui/ui/widgets/tree_view.py`
- `new_gui/ui/widgets/bounded_combo.py`
- `new_gui/ui/widgets/notifications.py`

### Move Out
- `TreeViewEventFilter`
- `ColorTreeView`
- `BoundedComboBox`
- `NotificationWidget`
- `NotificationManager`

### Keep In Place
- usage sites in `MainWindow`
- instance creation order
- signal connections

### Expected Net Reduction
- about 540-560 lines

### Validation
- `python3 -m py_compile ...`
- `import new_gui.reproduce_ui`
- confirm widget imports and `MainWindow` startup still work
- result: completed, file reduced to about 2648 lines

## Slice 2
Status: completed
Goal: move large UI builder method bodies out while keeping wrapper methods in `MainWindow`

### Create
- `new_gui/ui/builders/window_builder.py`
- `new_gui/ui/builders/menu_builder.py`
- `new_gui/ui/builders/top_panel_builder.py`
- `new_gui/ui/builders/shortcut_builder.py`

### Move Bodies Out
- `_init_window`
- `_init_menu_bar`
- `_init_top_panel`
- `_setup_keyboard_shortcuts`
- `_position_top_action_buttons`

### Wrapper Shape
Each `MainWindow` method should remain, but become a thin delegating wrapper.

### Expected Net Reduction
- about 590-605 lines

### Validation
- compile
- startup smoke test
- verify top panel, menu bar, and shortcut behavior in GUI
- result: completed, file reduced to about 2034 lines

## Slice 3
Status: completed
Goal: move theme orchestration and top-panel background handling out of `reproduce_ui.py`

### Create
- `new_gui/ui/controllers/theme_controller.py`

### Move Bodies Out
- `apply_theme`
- `_init_top_panel_background`
- `_toggle_theme`
- `_get_xmeta_background_color`

### Expected Net Reduction
- about 315-320 lines

### Validation
- compile
- startup smoke test
- verify tree colors, top panel background, tab colors, and scrollbar colors
- result: completed, file reduced to about 1715 lines

## Slice 4
Status: completed
Goal: move view refresh and view-state orchestration bodies out of `reproduce_ui.py`

### Create
- `new_gui/ui/controllers/view_controller.py`

### Move Bodies Out
- `populate_data`
- `change_run`
- `filter_tree`
- `_filter_tree_by_status_flat`
- `_apply_status_filter`
- `close_tree_view`
- `show_all_status`
- `restore_normal_view`
- `on_run_changed`
- column-width helpers
- restore-plan wrappers
- run-view activation helpers

### Expected Net Reduction
- about 320-330 lines

### Validation
- compile
- main view regression
- search regression
- status view regression
- trace view regression
- snapshot restore regression
- result: completed, added `new_gui/ui/controllers/view_controller.py`, compile passed, import smoke test passed, file reduced to about 1381 lines

## Slice 5
Status: completed
Goal: move action and context-menu orchestration bodies out of `reproduce_ui.py`

### Create
- `new_gui/ui/controllers/action_controller.py`
- `new_gui/ui/controllers/context_menu_controller.py`

### Move Bodies Out
- `start`
- `on_tree_double_clicked`
- `show_context_menu`
- menu builders
- `retrace_tab`
- `create_tune`
- `copy_tune_to_runs`
- file open handlers
- tune handlers
- copy-path helper

### Expected Net Reduction
- about 410-425 lines

### Validation
- compile
- command execution regression
- tune create/copy regression
- context menu regression
- file open regression
- bsub edit regression
- result: completed, added `new_gui/ui/controllers/action_controller.py` and `new_gui/ui/controllers/context_menu_controller.py`, compile passed, import smoke test passed, file reduced to about 953 lines

## Stop Rule
Stop once `reproduce_ui.py` reaches about 950-1150 lines and remains understandable.
Do not continue splitting 3-5 line wrappers just to chase a smaller number.

## Current Recommendation
- Stop structural splitting here for now
- Focus on inner-network regression for execute, context menu, tune, trace, and file-open flows
- Keep `MainWindow` wrappers stable and avoid over-splitting tiny helper methods just to reduce line count
