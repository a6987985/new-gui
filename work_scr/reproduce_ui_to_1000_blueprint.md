# reproduce_ui.py to ~1000 Lines Blueprint

## Goal
Reduce `new_gui/reproduce_ui.py` from about 3215 lines to about 950-1150 lines while preserving:
- behavior
- layout tree
- widget creation order
- stylesheet output
- signal-slot wiring semantics
- runtime visual effect

This is not a redesign plan. This is a facade-thinning plan.
The file should remain the application entry and `MainWindow` definition, but large method bodies should move into external builder/controller modules.

## Current Size Snapshot
- `new_gui/reproduce_ui.py`: 3215 lines
- `MainWindow`: 2544 lines
- Largest remaining blocks:
  - `_init_top_panel`: 443 lines
  - `_init_top_panel_background`: 189 lines
  - `apply_theme`: 134 lines
  - `_init_menu_bar`: 87 lines
  - `populate_data`: 71 lines
  - `_setup_keyboard_shortcuts`: 61 lines
  - `create_tune`: 57 lines
  - `copy_tune_to_runs`: 49 lines
  - `start`: 47 lines
  - `change_run`: 47 lines

## Reality Check
Getting to around 1000 lines is possible, but only if `reproduce_ui.py` becomes a thin facade:
- keep `MainWindow`
- keep method names
- keep signal connection points in `MainWindow`
- keep startup entry here
- move method bodies out

If we insist that most method bodies still live in `reproduce_ui.py`, then 1000 lines is not realistic.

## Target Shape
Final `reproduce_ui.py` should contain mainly:
- imports
- Qt app entry
- `MainWindow` state fields
- thin wrappers that delegate to external modules
- only the most timing-sensitive UI glue that truly must stay inline

Expected final line range after safe execution:
- conservative: 1100-1300
- aggressive but still realistic: 950-1150

## Budget Summary
Starting point: about 3215 lines

### Slice 1: Move Remaining In-File Custom Widgets
Create:
- `new_gui/ui/widgets/tree_view.py`
- `new_gui/ui/widgets/bounded_combo.py`
- `new_gui/ui/widgets/notifications.py`

Move out:
- `TreeViewEventFilter` (59)
- `ColorTreeView` (62)
- `BoundedComboBox` (220)
- `NotificationWidget` (125)
- `NotificationManager` (95)

Gross reduction: about 561 lines
Net reduction: about 540-560 lines
Remaining estimate: about 2655 lines

Risk: Low
Reason:
- these are already self-contained classes
- no need to change `MainWindow` behavior
- only import paths change

### Slice 2: Extract UI Builder Bodies
Create:
- `new_gui/ui/builders/menu_builder.py`
- `new_gui/ui/builders/top_panel_builder.py`
- `new_gui/ui/builders/shortcut_builder.py`
- optionally `new_gui/ui/builders/window_builder.py`

Move method bodies out, keep same method names in `MainWindow` as wrappers:
- `_init_menu_bar` (87)
- `_init_top_panel` (443)
- `_setup_keyboard_shortcuts` (61)
- `_init_window` (22)
- `_position_top_action_buttons` (12)

Gross reduction: about 625 lines
Wrapper cost: about 20-30 lines
Net reduction: about 590-605 lines
Remaining estimate: about 2050 lines

Risk: Medium
Reason:
- widget creation order must remain identical
- signal connection code must not move across phases casually
- styles must be copied byte-for-byte where possible

Execution rule:
- wrappers remain in `MainWindow`
- wrappers call builder functions like `top_panel_builder.init_top_panel(self)`
- no control flow change during the move

### Slice 3: Extract Theme Application Body
Create:
- `new_gui/ui/controllers/theme_controller.py`

Move out:
- `apply_theme` (134)
- `_init_top_panel_background` (189)
- `_toggle_theme` (5)
- `_get_xmeta_background_color` (4)

Gross reduction: about 332 lines
Wrapper cost: about 12-16 lines
Net reduction: about 315-320 lines
Remaining estimate: about 1730 lines

Risk: Medium
Reason:
- touches many widgets and style strings
- still safe if `self` is passed through and style text is not rewritten

### Slice 4: Extract View Refresh / View-State Orchestration Bodies
Create:
- `new_gui/ui/controllers/view_controller.py`

Move out:
- `populate_data` (71)
- `change_run` (47)
- `filter_tree` (41)
- `_filter_tree_by_status_flat` (32)
- `_apply_status_filter` (12)
- `close_tree_view` (30)
- `show_all_status` (15)
- `restore_normal_view` (4)
- `on_run_changed` (3)
- `_apply_all_status_column_widths` (26)
- `_get_header_min_widths` (20)
- `_get_main_view_default_column_widths` (20)
- `_get_main_view_default_window_width` (7)
- `_apply_initial_window_width` (7)
- `_activate_selected_run_view` (22)
- `_build_current_view_restore_plan` (5)
- `_restore_view_from_plan` (15)

Gross reduction: about 377 lines
Wrapper cost: about 45-55 lines
Net reduction: about 320-330 lines
Remaining estimate: about 1400 lines

Risk: Medium-High
Reason:
- this is now true UI orchestration, not pure data helpers
- must preserve current refresh order exactly
- must preserve snapshot restore behavior exactly

Execution rule:
- keep all public `MainWindow` method names the same
- only move bodies
- reuse current `services/view_*` helpers from the controller instead of from `MainWindow` directly

### Slice 5: Extract User Action Orchestration Bodies
Create:
- `new_gui/ui/controllers/action_controller.py`
- `new_gui/ui/controllers/context_menu_controller.py`

Move out:
- `start` (47)
- `on_tree_double_clicked` (42)
- `show_context_menu` (33)
- `_build_execute_menu` (29)
- `_build_file_menu` (19)
- `_build_tune_menu` (25)
- `_build_params_menu` (11)
- `_build_trace_menu` (17)
- `_build_copy_menu` (12)
- `retrace_tab` (32)
- `create_tune` (57)
- `copy_tune_to_runs` (49)
- `handle_tune` (24)
- `open_user_params` (16)
- `open_tile_params` (13)
- `handle_csh` (12)
- `handle_log` (12)
- `handle_cmd` (12)
- `open_terminal` (6)
- `_open_file_with_editor` (9)
- `_copy_run_path` (6)

Gross reduction: about 483 lines
Wrapper cost: about 60-70 lines
Net reduction: about 410-425 lines
Remaining estimate: about 980-990 lines

Risk: High
Reason:
- this is the slice that gets us to the number target
- these methods are not pure; they interact with dialogs, notifications, selection state, refresh state, and external commands
- still feasible if we keep `MainWindow` wrappers and treat controller functions as body-hosts only

## Recommended Final Module Layout

### UI Widgets
- `new_gui/ui/widgets/tree_view.py`
  - `TreeViewEventFilter`
  - `ColorTreeView`
- `new_gui/ui/widgets/bounded_combo.py`
  - `BoundedComboBox`
- `new_gui/ui/widgets/notifications.py`
  - `NotificationWidget`
  - `NotificationManager`

### UI Builders
- `new_gui/ui/builders/window_builder.py`
- `new_gui/ui/builders/menu_builder.py`
- `new_gui/ui/builders/top_panel_builder.py`
- `new_gui/ui/builders/shortcut_builder.py`

### UI Controllers
- `new_gui/ui/controllers/theme_controller.py`
- `new_gui/ui/controllers/view_controller.py`
- `new_gui/ui/controllers/action_controller.py`
- `new_gui/ui/controllers/context_menu_controller.py`

## What Must Stay in reproduce_ui.py
Keep these in the entry file even after aggressive thinning:
- imports and startup entry
- `MainWindow` class definition
- `__init__`
- `_init_core_variables`
- tiny wrappers that preserve method names currently referenced by signals or internal callers
- any tiny glue method where moving it saves almost no lines but increases indirection

## What Should Not Be Chased Further
After the file reaches around 950-1150 lines, stop.
At that point, further shrinking is likely to hurt readability more than it helps.
Do not try to reduce below ~900 by splitting every 3-5 line wrapper.

## Safe Execution Order
1. Move remaining widget classes
2. Move builders (`menu`, `top_panel`, `shortcut`, maybe `window`)
3. Move theme application
4. Move view refresh orchestration
5. Move action/context menu orchestration
6. Stop and reassess

## Guardrails
For every slice:
- move code first, refactor later
- keep method names stable
- keep signal connections in the same phase and same order
- do not rewrite stylesheet strings unless absolutely necessary
- preserve `MainWindow` field access through `self`
- compile after each slice
- run inner-network regression after each high-risk slice

## Practical Recommendation
If the goal is only maintainability, stop around 1200-1400 lines.
If the goal is specifically to make `reproduce_ui.py` look like a clean entry facade, continue to around 950-1150 lines.

I do not recommend targeting a number lower than that.
