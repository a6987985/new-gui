# Dependency Graph Closure Checklist

## Goal

Close the dependency-graph module at a stable maintenance boundary without expanding it into a second primary workspace.

## Completed

### 1. Remove duplicate rebuild risk in `Locate In Tree`

- Status: Completed
- Action:
  - Stop relying on `QComboBox.currentIndexChanged` side effects during graph-to-tree return
  - Switch runs silently when needed
  - Rebuild the tree exactly once through the explicit activation path
- Result:
  - Graph return no longer depends on a double-triggered run activation flow

### 2. Preserve tree context when returning from graph whenever possible

- Status: Completed
- Action:
  - Capture a graph return context when opening the dialog
  - Restore search, trace, and status-filter tree contexts before selecting the located target
  - Fall back to the main run view only when the requested target is outside the original filter scope
- Result:
  - `Locate In Tree` now preserves analysis context when it can, and degrades explicitly when it cannot

## Remaining Low-Priority Cleanup

### 3. Clarify local-scope trace semantics under depth-limited mode

- Status: Completed
- Action:
  - Make local-scope semantics explicit in the graph UI
  - Define `Depth` as a visual scope control for the rendered local subgraph
  - Define `Trace Up / Trace Down` as operating within the current graph scope
- Result:
  - The graph now clearly communicates that `Depth` limits what is shown, while trace actions stay inside the active local scope

### 4. Reduce redraw cost for repeated local/full toggles

- Status: Pending
- Reason:
  - Scope switches currently rebuild the full scene each time
- Recommendation:
  - Keep current behavior unless real graph size makes redraw latency visible

## Final Boundary

The dependency graph should remain:

- Single-run
- Read-only
- Modal
- Focused on inspection and navigation

It should not expand into:

- A graph editor
- A multi-run comparison workspace
- A permanently synchronized second tree view
- A feature-heavy canvas with many more toolbar controls
