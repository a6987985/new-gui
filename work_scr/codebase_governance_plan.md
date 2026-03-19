# New-GUI Codebase Governance Plan

> Created: 2026-03-19
> Status: Active
> Scope: `new_gui/`
> Primary intent: reduce localized "big ball of mud" growth without destabilizing the GUI

## 1. Why This Document Exists

The project is no longer in a "stop splitting" state for all core modules.

Earlier maintenance notes were reasonable when `MainWindow` had already been reduced and the main
goal was to avoid over-refactoring. That assumption is no longer fully true. The codebase has
grown again around several high-coupling UI hotspots, especially in the main window, the top-panel
logic, and the dependency-graph dialog.

This document is the governance baseline for the next cleanup phase.

It does not call the whole project a full trash heap.
It does say that some modules are already trending into localized mud zones and should be treated
as active debt owners.

## 2. Current Diagnosis

### Size snapshot

Current `.py` line counts:

| Module | Lines | Governance signal |
|---|---:|---|
| `new_gui/reproduce_ui.py` | 1602 | overloaded orchestration root |
| `new_gui/ui/dialogs/dependency_graph.py` | 1045 | mixed state, rendering, and interaction |
| `new_gui/ui/builders/top_panel_builder.py` | 774 | mixed layout, style, sizing policy, and behavior glue |
| `new_gui/ui/dialogs/params_editor.py` | 596 | large, but currently secondary priority |
| `new_gui/ui/controllers/view_controller.py` | 520 | acceptable only if it stays orchestration-focused |
| `new_gui/ui/controllers/action_controller.py` | 468 | growing coordination surface |

### What is actually wrong

1. `MainWindow` is still a God Object.
- It owns startup, lifecycle, tree state, search sync, top-button settings, bottom output panel
  behavior, logging sink behavior, dependency graph launching, and many compatibility wrappers.

2. `top_panel_builder.py` is not just a builder anymore.
- It mixes style tokens, geometry measurement, row layout policy, and floating-button rebuild logic.

3. `dependency_graph.py` combines too many roles.
- Dialog shell, graph state, search behavior, drawing, interaction handling, and export all live in
  one file.

4. Controllers still depend on a wide `window` surface.
- Several flows are split physically, but not yet narrowed architecturally.

5. Visual styling is still too distributed.
- Inline stylesheet strings across widgets make coordinated UI changes slower and riskier.

## 3. Governance Decision

The previous "do not split further for now" guidance should be treated as partially expired for the
modules listed below:

- `new_gui/reproduce_ui.py`
- `new_gui/ui/builders/top_panel_builder.py`
- `new_gui/ui/dialogs/dependency_graph.py`

It still remains valid for custom Qt behavior islands where the code is specialized, stable, and
not the current source of growth pressure.

## 4. Non-Goals

This governance plan is not a rewrite plan.

Do not do any of the following under the name of cleanup:

- replace PyQt5
- redesign the visual layout while doing structural work
- rename stable signal-facing methods without a compatibility reason
- chase line count reduction as a goal by itself
- move code into more files if ownership is not actually improved
- introduce a theoretical architecture that increases runtime indirection without reducing coupling

## 5. Governance Principles

1. Preserve runtime behavior first.
- Existing actions, shortcuts, menus, and tree behavior are the baseline.

2. Extract ownership, not just lines.
- A move is good only if the destination module has a clear reason to own that logic.

3. Keep `MainWindow` as the lifecycle root, but not as the implementation owner of every feature.

4. Preserve signal-facing method names when they are already referenced by menus, shortcuts, or Qt
   wiring.

5. Move cohesive clusters together.
- Do not scatter one feature across builder, controller, and service files unless the ownership
  split is obvious.

6. Add cheap regression coverage before medium-risk moves.

## 5.1 Behavior Freeze Contract

This governance pass is a structural cleanup pass, not a product redesign pass.

Unless the user explicitly approves a visible product change, the following must remain frozen:

1. GUI main structure
- Do not change the visible page hierarchy of the main window.
- Do not change the main placement relationship of menu bar, top panel, tree area, bottom output
  area, dialogs, or status area.
- Do not change default widget ordering, layout bands, or panel roles.

2. Feature semantics
- Do not change what existing actions do.
- Do not change menu meanings, shortcut meanings, or button meanings.
- Do not remove or rename stable user-facing actions as part of cleanup.

3. Style output
- Do not intentionally change colors, paddings, borders, spacing, typography, or tab/button visual
  language during structural refactors.
- If styles are moved to a new owner, the rendered result should remain visually equivalent.

4. Interaction feel
- Do not intentionally change click flow, focus behavior, hover behavior, panel expansion rules, or
  other established interaction rhythms.
- Fixes for confirmed bugs are allowed, but they must be called out as behavior changes rather than
  hidden under "refactor".

Allowed change scope during governance work:

- move logic across modules
- narrow ownership boundaries
- remove duplication
- add thin compatibility wrappers
- add smoke checks and internal helpers

Not allowed without explicit approval:

- layout redesign
- feature redesign
- style refresh
- UX flow changes
- interaction timing changes that a user can feel

## 6. Priority Backlog

### Phase 0. Stop Debt Growth

Objective:
- Prevent new features from making the hotspots worse while cleanup is ongoing.

Checklist:
- Do not add new non-trivial feature bodies directly into `MainWindow` unless the code is truly
  lifecycle-only.
- Do not add new sizing policy or style policy into `top_panel_builder.py` unless it directly
  belongs to existing top-button logic.
- Do not add new interaction modes directly into `dependency_graph.py` without first assigning an
  owner for state vs rendering.
- Require every medium-risk refactor to pass at least:
  - `py_compile`
  - one offscreen Qt smoke check
  - one manual GUI sanity pass on tree, search, run switching, and actions

Exit criteria:
- No new large feature body lands in the three hotspot modules without an owner note.

### Phase 1. Slim `MainWindow`

Objective:
- Reduce `reproduce_ui.py` from implementation-heavy to orchestration-heavy.

Recommended extraction order:

1. Bottom output and GUI log flow.
- Extract ownership for:
  - GUI log handler install/remove
  - queued GUI log append path
  - bottom output panel show/hide and tab-switch behavior
- Keep in `MainWindow`:
  - lifecycle root calls
  - signal-facing wrappers if needed

2. Search-sync and filter bridge logic.
- Extract ownership for:
  - top search <-> header filter synchronization
  - current search restore helpers
  - search UI state coordination that is not lifecycle-sensitive

3. Settings popups for column visibility and button visibility.
- Extract ownership for:
  - picker creation
  - picker refresh
  - apply/cancel orchestration
- Leave only menu entrypoints in `MainWindow`

4. Tree-build bridge helpers that are still too fat.
- Review whether these should stay in `MainWindow` or move behind a dedicated presenter/helper:
  - `_build_target_row_items`
  - `_append_display_node_to_parent`
  - `_append_target_groups_to_model`
- These are acceptable to keep only if they become thin adapters over service-level builders.

Do not move yet:
- startup object creation order
- watcher/timer wiring
- application shutdown and executor ownership

Exit criteria:
- `MainWindow` keeps the same public behavior surface
- implementation-heavy helper clusters are reduced or moved
- `reproduce_ui.py` trends toward lifecycle/orchestration instead of local feature ownership

### Phase 2. Split `top_panel_builder.py` By Responsibility

Objective:
- Separate top-panel structure from top-button sizing and style policy.

Target sub-owners:

1. Static definitions
- button ids
- button metadata
- stable row defaults

2. Style and sizing policy
- button style tokens
- text-to-width measurement rules
- fixed-height policy
- row spacing policy

3. Layout construction
- widget creation
- row widget assembly
- anchor and geometry application

4. Settings integration hooks
- only small hooks that connect the builder to the visibility picker flow

Recommended shape:
- keep `init_top_panel(...)` as the public builder entry
- move width/height measurement and row-fit policy into a dedicated helper module
- move reusable style blocks into a style owner instead of leaving them inline beside geometry code

Exit criteria:
- no single file owns static definitions, style tokens, geometry policy, and widget assembly all at
  once
- row1/row2 width logic remains behavior-identical after the split

### Phase 3. Break `dependency_graph.py` Into Real Layers

Objective:
- Make future graph work possible without editing a 1000+ line dialog every time.

Recommended split:

1. Dialog shell
- owns toolbar/widgets
- owns high-level signals
- owns status/info messaging only

2. Graph state/controller
- owns current target
- owns local/full graph mode
- owns search match state
- owns trace direction state

3. Rendering layer
- owns node placement
- owns level guides
- owns edge drawing
- owns selection/highlight repaint behavior

4. Export and utility helpers
- PNG export
- trace target collection helpers
- status label/color normalization helpers if they are rendering-specific

Do not over-split:
- interactive node item can remain near rendering logic if that keeps the Qt coupling simpler

Exit criteria:
- dialog shell no longer contains the full search, draw, trace, and export implementation bodies
- graph rendering changes do not require editing unrelated dialog control code

### Phase 4. Narrow Controller Coupling

Objective:
- Reduce how much controller code needs to know about the entire `window` object.

Checklist:
- Review `action_controller.py` and `view_controller.py` for wide `window` assumptions
- group related window access behind narrow helper methods or small context objects where helpful
- standardize action result logging and notification flow through one append path
- remove duplicate orchestration paths that do the same UI refresh in slightly different ways

Important rule:
- do not replace the current controller approach with a large framework abstraction
- prefer incremental narrowing over a big controller rewrite

Exit criteria:
- controllers operate on smaller, clearer dependency surfaces
- new actions can reuse a common logging/notification pattern

### Phase 5. Consolidate Style Ownership

Objective:
- Make visual tuning cheaper and less fragile.

Checklist:
- identify repeated button style patterns used across widgets
- move repeatable style tokens into shared style owners where it improves consistency
- keep widget-local styles only for truly local behavior
- document which visual areas are theme-driven vs widget-local

Immediate candidates:
- bottom output panel
- embedded terminal controls
- top-panel button styles
- popup action buttons

Exit criteria:
- small UI refreshes do not require hunting through many unrelated widget files

### Phase 6. Add A Cheap Regression Harness

Objective:
- Make medium-risk refactors safe enough to continue.

Checklist:
- import smoke for the main package
- `py_compile` script or quality gate for touched modules
- offscreen smoke for:
  - `BottomOutputPanel`
  - top-panel initialization
  - dependency graph dialog construction
- one scripted action smoke for:
  - command result logging
  - notification mirroring
  - button visibility apply flow

Exit criteria:
- every governance-phase refactor has at least one repeatable automated safety check

## 7. Execution Order

Recommended order:

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 6
5. Phase 3
6. Phase 4
7. Phase 5

Reason:
- `MainWindow` and top-panel debt are the biggest growth multipliers
- regression automation should be added before deeper dialog work
- styling consolidation is valuable, but not the first blocker for maintainability

## 8. Practical Review Gates

Treat a module as requiring governance review when one or more of these are true:

- file size is above 600 lines and still growing
- one file owns both UI structure and behavior policy
- one class owns both rendering and orchestration
- a controller keeps needing new `window` attributes for each feature
- a visual tweak requires synchronized edits across multiple unrelated files

## 9. Definition Of Done For This Governance Pass

This pass is successful when:

- `MainWindow` is clearly the orchestration root instead of the default implementation bucket
- `top_panel_builder.py` is split by responsibility, not by arbitrary file count
- `dependency_graph.py` is no longer a monolithic dialog island
- controller-to-window coupling is reduced
- cheap smoke coverage exists for the high-risk UI seams
- the next feature can be added without re-growing the same hotspots immediately

## 10. Tracking Template

Use this when opening future cleanup tasks:

```text
Task:
Owner:
Hotspot:
Why now:
What moves:
What must stay:
Regression checks:
Exit criteria:
```
