# Main View Graph Tabs Handoff

## Session Snapshot

- Branch: `feat-main-view-graph-tabs`
- Current HEAD: `204b40e0e1535c915d6b42ad117c9c41eb79d5ac`
- Source plan: `docs/superpowers/plans/2026-04-13-main-view-graph-tabs.md`

## Completed Items

### Task 1: Add the Content Tab Shell

Status: done and review-approved

Commits:
- `8f00b1c` Add content mode tab shell
- `59d709c` Disable unfinished dependency graph tab

Delivered:
- Added persistent content tab shell for `Main View` and `Dependency Graph`
- Added graph-related window state fields in `MainWindow._init_core_variables()`
- Kept `Main View` as the active page by default
- Explicitly disabled the unfinished `Dependency Graph` tab to avoid exposing an empty surface
- Added and expanded regression tests for the shell and default state contract

Main files touched:
- `new_gui/main.py`
- `new_gui/presentation/views/builders/top_panel_builder.py`
- `tests/test_main_content_graph_tabs.py`

### Task 2: Extract an Embeddable Dependency Graph Panel

Status: done and review-approved

Commits:
- `e45e5ac` Extract dependency graph panel
- `204b40e` Test dialog graph compatibility layer

Delivered:
- Extracted the graph UI and behavior into `DependencyGraphPanel(QWidget)`
- Reused existing dependency-graph mixins instead of rewriting graph behavior
- Converted `DependencyGraphDialog` into a thin wrapper with `graph_panel`
- Preserved legacy dialog access through compatibility forwarding
- Added dialog-level compatibility coverage and fixed state-write forwarding

Main files touched:
- `new_gui/presentation/views/widgets/dependency_graph_panel.py`
- `new_gui/presentation/views/dialogs/dependency_graph.py`
- `tests/test_main_content_graph_tabs.py`

Verified during this session:
- `QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_main_content_graph_tabs -v`
- Existing dependency graph smoke flow remained compatible after the panel extraction

## Pending Items

### Task 3: Add Lazy Graph Tab Activation and Sidebar Coordination

Still to do:
- Create `new_gui/presentation/presenters/content_tab_controller.py`
- Wire `show_dependency_graph()` to activate the content tab instead of opening the old dialog path
- Lazy-build the embedded graph panel only when the graph tab is activated
- Re-enable the graph tab at the point this task is implemented
- Hide the left sidebar while the graph tab is active
- Restore sidebar visibility when returning to `Main View`
- Add tests from Task 3 in the source plan

### Task 4: Add Dirty Refresh, Locate-In-Tree Return, and Theme Compatibility

Still to do:
- Add deferred refresh behavior with `_mark_dependency_graph_dirty()`
- Refresh the embedded graph only when re-entering the graph tab after dirty state
- Ensure `locate_target_in_tree()` switches back to `Main View`
- Connect graph refresh to run/theme changes without leaking tree filters into graph state
- Add tests from Task 4 in the source plan

### Task 5: Add Smoke Coverage and Final Regression Verification

Still to do:
- Extend `new_gui/infrastructure/tools/governance_smoke.py` for the new content-tab flow
- Add panel reuse regression coverage
- Run the final verification commands from the source plan

## Important Notes For The Next Session

- Task 1 intentionally leaves the `Dependency Graph` content tab disabled. That is expected until Task 3 wires real activation.
- Task 2 already moved the graph body into `DependencyGraphPanel`. The next session should reuse that panel instead of rebuilding graph UI in presenters or builders.
- `DependencyGraphDialog` now relies on compatibility forwarding. Tests already cover both read and write compatibility paths that mattered in this session.
- There are pre-existing untracked files in the worktree that were not part of this task:
  - `.superpowers/`
  - `docs/superpowers/plans/2026-04-13-main-view-graph-tabs.md`
  - `tests/test_linux_rendering_policy.py`
  - `tests/test_sidebar_toggle_transition.py`
  - `tests/test_workspace_sidebar.py`

## Recommended Resume Point

Resume from Task 3 in `docs/superpowers/plans/2026-04-13-main-view-graph-tabs.md` and keep the same subagent-driven workflow:
1. implement Task 3
2. spec review
3. code quality review
4. move to Task 4 only after Task 3 is approved
