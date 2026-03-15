# Dependency Graph Evolution Roadmap

## Goal

Evolve the dependency graph from a useful visualization helper into a more reliable analysis aid without changing its current role in the product.

The dependency graph should remain:

- A single-run analysis view
- Read-only
- Fast to open
- Consistent with the main tree view

It should not become a heavy graph editor or a second primary navigation surface.

## Current Position

Today the dependency graph already provides real value:

- It visualizes the run dependency structure by level
- It overlays runtime status on top of dependency structure
- It supports node selection, path tracing, zoom, pan, fit, reset, and PNG export

However, it still has clear product and implementation gaps:

- Graph tracing is not guaranteed to match the main tree trace semantics
- Legend and fallback status semantics can mislead users
- Large graphs become readable only with effort
- The graph is useful for inspection, but not yet efficient for focused diagnosis

## Design Direction

The module should evolve as a focused analysis companion for the main tree view.

Priority order:

1. Semantic correctness
2. Focused analysis workflows
3. Large-graph readability
4. Export polish

Avoid adding broad feature surface before those four areas are stable.

## Quick Wins

These changes are low-risk and should improve clarity immediately.

### 1. Generate legend from `STATUS_CONFIG`

Problem:

- The current legend is partially hard-coded
- It does not fully match the real status palette and available statuses

Target:

- Build the legend directly from `STATUS_CONFIG`
- Include every displayed status that can appear in the graph

Expected result:

- No color drift between graph, tree view, and status bar

### 2. Separate `unknown` from `pending`

Problem:

- Missing or unresolved status is currently presented as if it were `pending`

Target:

- Introduce an explicit display concept such as `unknown` or `no status`
- Keep `pending` reserved for real flow status only

Expected result:

- Users can distinguish missing data from queued work

### 3. Fit the graph automatically on first open

Problem:

- The dialog sets a scene rect but does not actually fit the rendered graph on initial display

Target:

- Automatically run `fit_view()` after drawing completes

Expected result:

- Users see the full graph immediately after opening the dialog

### 4. Elide long node labels

Problem:

- Long target names reduce readability and create visual crowding in dense graphs

Target:

- Show truncated labels in-node
- Keep the full name in tooltip

Expected result:

- Better readability without losing information

### 5. Focus on the currently selected target when opening the graph

Problem:

- The graph always opens at the full-run scope without carrying the user's current context

Target:

- Detect the currently selected target in the main tree
- Select and visually focus that node on dialog open when possible

Expected result:

- Better continuity between tree analysis and graph analysis

### 6. Improve empty-state and summary messaging

Problem:

- Graphs with no data or very large data sets do not explain themselves well

Target:

- Show node count, edge count, and level count in the info area
- Improve the no-data message

Expected result:

- Faster interpretation of what the dialog is showing

### 7. Align graph wording with main-view trace wording

Problem:

- Trace-related wording is not fully aligned across the graph and tree workflows

Target:

- Standardize labels, tooltips, and info text for trace actions

Expected result:

- Lower cognitive load and clearer user expectations

## Medium

These items provide the strongest functional improvement after the quick wins.

### 1. Unify graph trace semantics with main-tree trace semantics

Problem:

- The main tree and graph do not currently guarantee identical upstream and downstream trace results

Target:

- Define one authoritative dependency interpretation path
- Make graph trace and tree trace use the same semantic source

Expected result:

- Users trust that both views describe the same dependency truth

Notes:

- This is the single most important medium-priority item

### 2. Add in-graph target search

Problem:

- Large graphs are hard to navigate manually even with zoom and pan

Target:

- Add a small search field to locate, select, and center a target node

Expected result:

- Faster navigation in medium and large graphs

### 3. Add local subgraph mode

Problem:

- Full-run graphs are often too broad for focused investigation

Target:

- Support focused rendering for one selected target and its local upstream/downstream neighborhood
- Allow either full reachable subgraph or a limited-depth version

Expected result:

- The graph becomes practical for day-to-day root-cause inspection

### 4. Add graph-to-tree and tree-to-graph linking

Problem:

- The graph and main tree still behave as mostly isolated views

Target:

- Clicking a graph node should help locate the corresponding tree target
- Opening the graph from the tree should preserve current focus

Expected result:

- The graph becomes a companion analysis tool instead of a detached dialog

### 5. Make level structure more explicit

Problem:

- Levels are implied by vertical placement but not clearly labeled

Target:

- Add visible level markers, separators, or lane labels

Expected result:

- Faster structural understanding, especially in wide graphs

### 6. Improve de-emphasis behavior during trace

Problem:

- Non-highlighted nodes fade, but the visual hierarchy could be stronger

Target:

- Further reduce prominence of non-selected, non-traced regions
- Keep traced path visually dominant

Expected result:

- Better path readability in dense graphs

### 7. Improve export output quality

Problem:

- PNG export is functional but minimal

Target:

- Include run name, export time, and basic graph metadata in exported output when reasonable

Expected result:

- More useful artifacts for sharing and debugging records

## Not Recommended

These ideas are intentionally out of scope for now.

### 1. Do not add a heavy auto-layout engine yet

Reason:

- Integration cost is high
- Behavior tuning is difficult
- Current graph needs focus and semantic fixes first

### 2. Do not make the graph editable

Reason:

- The module is an analysis surface, not an editor
- Editing would introduce model synchronization risk and much higher complexity

### 3. Do not build multi-run comparison graph workflows yet

Reason:

- That changes the module from a run inspector into a comparison product
- The current pain points are still inside single-run workflows

### 4. Do not continue expanding the toolbar without workflow wins

Reason:

- More buttons do not solve the current discoverability and focus issues
- Search, focus, and local subgraphs have much higher value

### 5. Do not promote the graph into a second primary navigation mode

Reason:

- The main tree remains the correct primary workflow surface
- The graph should stay a specialist analysis companion

## Recommended Delivery Order

### Phase 1

Implement these first:

1. Legend from `STATUS_CONFIG`
2. `unknown` vs `pending`
3. Initial auto-fit
4. Long-label elision
5. Initial selected-target focus

Success criteria:

- The graph opens cleanly
- The graph is visually trustworthy
- The current target context is preserved

### Phase 2

Implement these next:

1. Unified trace semantics
2. In-graph search
3. Local subgraph mode

Success criteria:

- Trace results match the main view
- Medium and large graphs become practical to inspect

### Phase 3

Implement these only after Phase 2 is stable:

1. Graph/tree linking
2. Explicit level presentation
3. Stronger de-emphasis styling
4. Export enhancements

Success criteria:

- The graph becomes a polished analysis companion for ongoing use

## Acceptance Criteria

The dependency graph should be considered improved only if all of the following are true:

- Graph trace results match main-tree trace expectations
- Colors and legend entries match the real status system
- Opening the graph preserves useful user context
- Large graphs are easier to read without introducing feature clutter
- Export remains functional
- The dialog still opens fast for normal run sizes

## Suggested File Ownership

Likely implementation areas:

- Data semantics: `new_gui/services/run_dependency.py`
- Dialog behavior and rendering: `new_gui/ui/dialogs/dependency_graph.py`
- Entry-point context handoff: `new_gui/reproduce_ui.py`

If future work starts crossing into global workflow behavior, that should be introduced carefully rather than pushing all new responsibilities into the dialog class.
