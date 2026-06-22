# Main View Graph Tabs Design

**Date:** 2026-04-13

## Goal

Promote the current `Dependency Graph` capability from a menu-launched dialog to a first-class main-page view inside the primary application workspace, while preserving the existing `TreeView` workflow and keeping `TreeView` behavior unchanged when users switch back.

The approved interaction model is:

- keep `Main View` and `Dependency Graph` as two persistent content tabs in the main window
- place the new `Dependency Graph` tab to the right of the existing `Main View`
- use lazy loading for the graph tab
- share run, theme, status, and selected-target context
- do not share `TreeView` filtering state with the graph tab

## Context

Today the main workspace is effectively organized as:

- top control panel
- a custom tab-like header used by the current `TreeView` states
- left workspace sidebar
- right main content area containing the `TreeView` and bottom output panel

`Dependency Graph` currently does not live in that main workspace. It is launched from the menu bar or `Ctrl+G` and opens as a modal `QDialog`.

That creates three problems:

1. The graph is not a peer view of the main content.
2. The dialog-based graph has separate lifecycle and navigation semantics from the main workspace.
3. The existing top pseudo-tab state is overloaded with `TreeView`-specific modes such as `Main View`, `All Status`, `Status Filter`, and `Trace`, but has no concept of a peer graph workspace.

## Approved Direction

Use **content-level tabs** inside the right side of the main workspace.

This means:

- keep the current top pseudo-tab system for `TreeView`-internal view states
- add a real `QTabWidget` in the main content area
- use that `QTabWidget` only for switching between:
  - `Main View`
  - `Dependency Graph`

The `Main View` tab will host the existing tree-and-output layout unchanged.
The `Dependency Graph` tab will host an embedded graph panel instead of a dialog.

This design intentionally avoids rewriting the current top pseudo-tab behavior in the same change. That keeps the `TreeView` compatibility surface smaller and reduces regression risk.

## UI Structure

### Main content composition

The main content region should become:

- left workspace sidebar
- right content-mode tab widget

The right content-mode tab widget should have two pages:

1. `Main View`
2. `Dependency Graph`

The current `_content_splitter` should be moved intact into the `Main View` page so that:

- the current `TreeView`
- the bottom output panel
- the external tree scrollbar
- the header filter
- the column sizing rules
- the context menu and double-click behaviors

all preserve their existing layout and parent-child relationships as much as possible.

### Dependency graph placement

The graph page should embed the graph UI directly into the content tab rather than opening `DependencyGraphDialog.exec_()`.

The graph page should preserve the current graph tool surface:

- zoom controls
- fit/reset
- search
- local focus scope
- full graph restore
- locate target in tree
- export PNG
- legend and graph metadata labels

### Sidebar behavior

The left workspace sidebar should remain visible and functional for `Main View`.

When `Dependency Graph` is the active content tab, the sidebar should be hidden or disabled and visually removed from the active workflow. This is required because the graph view does not share the tree filtering model, and leaving the sidebar active would imply a filtering contract that the graph tab does not honor.

## State Boundaries

### Shared state

The graph tab and tree tab should share:

- current run
- theme and active palette
- status colors and status cache
- current selected target from the tree as a graph focus hint

### Non-shared state

The graph tab must not inherit or be constrained by:

- stage/type sidebar filters
- header search text
- status-filter tree states
- trace-filter tree states
- `All Status` overview state
- tree column widths
- tree expanded/collapsed state
- tree scroll position

The graph tab should keep its own private state:

- graph zoom level
- graph search text and search match position
- local/full scope mode
- selected graph node
- graph highlight state

## Event Flow

### Run changes

`Main View` continues using the existing run-change path.

The graph tab should not rebuild immediately on every run change. Instead:

- mark the graph tab as `dirty`
- if the graph tab is not active, do nothing else
- if the graph tab is active, refresh after the run-change sequence completes

### Tree selection changes

The selected tree target is only a focus hint for the graph tab.

Rules:

- on first graph activation, use the current selected tree target as the initial focus target when available
- after the graph page is already active and the user has graph-local state, tree selection changes should not forcibly reset the graph state
- the graph should only re-apply tree-derived focus when:
  - it is first loaded
  - the run changes
  - the user explicitly invokes a locate/sync action

### Content-tab switching

From `Main View` to `Dependency Graph`:

- if the graph panel has never been created, create it and build graph data
- if the graph panel exists but is marked `dirty`, rebuild the full graph for the current run
- if the graph panel exists and is not `dirty`, just activate it

From `Dependency Graph` back to `Main View`:

- do not rebuild the tree
- do not reset tree filter, column, scroll, or expansion state
- restore sidebar visibility and normal tree interaction immediately

### Runtime updates

The runtime observer path should remain tree-first.

The graph page should not maintain live background updates while inactive. It refreshes only when:

- first activated
- reactivated after a run change
- explicitly refreshed while active

## Compatibility Rules

### Menu and shortcuts

The existing menu item and `Ctrl+G` shortcut should change behavior:

- no dialog launch
- activate the `Dependency Graph` content tab instead
- use the current run and selected tree target to drive initial graph focus

### Locate In Tree

The graph panel should keep `Locate In Tree`, but its behavior becomes:

- switch to `Main View`
- restore tree context as needed
- locate and select the requested target

### Top pseudo-tab states

The current top pseudo-tab states remain scoped to the `TreeView` world only:

- `Main View`
- `All Status Overview`
- `Status: ...`
- `Trace ...`

The new content-level tabs should not replace or reinterpret those states in this phase.

That means:

- content tabs express `Tree vs Graph`
- top pseudo-tabs continue to express `Tree internal presentation state`

## Implementation Shape

### 1. Content tab container

Add a real `QTabWidget` in the main-content area builder and move the existing `_content_splitter` into the `Main View` tab page.

This change belongs in the view/builder layer, primarily around the current main-content composition logic.

### 2. Embedded graph panel

Refactor the current `DependencyGraphDialog` so the reusable graph body lives in an embeddable widget such as `DependencyGraphPanel(QWidget)`.

The dialog shell may remain as a thin compatibility wrapper if needed, but the main workspace tab must use the embeddable panel directly.

### 3. View-mode coordinator

Add a dedicated coordinator in presenter/service land for:

- active content tab mode
- graph created/not created state
- graph dirty flag
- graph refresh scheduling
- tree-selection-to-graph-focus handoff

This state must stay separate from `is_all_status_view`. The latter continues to describe only `TreeView` presentation mode.

### 4. Compatibility bridges

Update menu and shortcut paths so all graph entry points converge on the content-tab activation path instead of dialog creation.

## Testing Strategy

### UI structure smoke

Add coverage for:

- two content tabs exist
- default active tab is `Main View`
- graph tab activation hides or disables the sidebar
- returning to `Main View` restores sidebar behavior

### Behavior tests

Add coverage for:

- graph tab is lazily initialized
- run change marks graph dirty without forcing immediate graph rebuild while inactive
- graph rebuild occurs on next activation
- tree selected target becomes the initial graph focus hint
- tree state survives a round trip to graph and back

### Regression tests

Add coverage for:

- `Ctrl+G` activates graph tab instead of opening a dialog
- `Locate In Tree` switches back to the tree tab and locates the target
- `All Status`, status filters, and trace filters remain tree-only states
- theme refresh still applies correctly to both tabs

## Non-Goals

This design does not include:

- rewriting the top pseudo-tab system into a full tab framework
- making graph filtering mirror tree filtering
- adding background live graph updates while the graph tab is inactive
- redesigning graph rendering itself

## Risks

### Mixed tab semantics

The application will temporarily have two tab layers:

- top pseudo-tabs for tree presentation state
- content tabs for tree vs graph mode

That is acceptable for this phase, but the state ownership must remain explicit in code and UI behavior.

### Dialog-to-widget extraction risk

`DependencyGraphDialog` currently assumes dialog lifecycle, focus, sizing, and shortcut behavior. Extracting a reusable embedded panel introduces a moderate refactor risk, especially around keyboard shortcuts and viewport sizing.

### Refresh drift

If the graph dirty flag is not managed carefully, the graph can become stale or rebuild too often. The lazy-load rules must stay narrow and test-covered.

### False filter expectations

If the sidebar remains active while the graph tab is visible, users may expect graph results to be filtered by sidebar category. Hiding or disabling the sidebar on graph activation avoids that mismatch.

## Verification Requirements

The feature is complete only when all of the following are true:

1. The main workspace shows both `Main View` and `Dependency Graph` as persistent content tabs.
2. The graph tab is lazily created and lazily refreshed according to the approved rules.
3. Switching to graph and back does not disturb tree state.
4. `Ctrl+G` and menu entry activate the graph tab instead of opening a dialog.
5. `Locate In Tree` returns from graph to tree correctly.
6. Existing tree-specific modes still behave as before within the `Main View` tab.

## Recommended Follow-Up

After this design document is approved in writing, create an implementation plan that breaks the work into:

- content-tab shell introduction
- graph panel extraction
- event/state coordination
- regression and smoke coverage
