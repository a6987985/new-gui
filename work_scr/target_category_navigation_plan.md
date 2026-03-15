# Target Category Navigation Plan

## Goal

Introduce a separate target-category definition file and expose it as a left-side
navigation panel in the GUI, while preserving the current main-tree structure and
all existing behaviors:

- `level -> generic group -> target`
- batch execute actions
- search / status / trace filters
- tab state and view restore
- current row styling and visual hierarchy

The main objective is to reduce reading density for large runs without rewriting
the existing tree semantics.

## Recommended Direction

Use **Scheme A**:

- add a left-side category navigation panel
- load category definitions from a separate config file
- keep the right-side target tree unchanged in structure
- apply category selection as an outer filtering scope

This gives the best balance between usability, implementation cost, and risk.

## Why Scheme A Is Preferred

### Benefits

- keeps the current tree data model stable
- avoids adding a new synthetic root layer above `level`
- reuses existing grouped tree rendering, execute actions, and status refresh logic
- matches the desired visual model of a left-side navigation rail
- can be introduced gradually with low UI disruption

### Tradeoffs

- category state becomes an additional view dimension
- restore logic must remember category scope together with search/status/trace mode
- overlapping category membership must be defined explicitly

## Alternatives Considered

### Scheme B: Left Navigation as Jump/Locate Only

Left navigation would scroll to or select matching targets in the existing tree,
but would not filter the tree contents.

#### Pros

- lowest implementation risk
- minimal changes to current data flow
- useful for validating category definitions early

#### Cons

- does not materially reduce reading density
- feels more like an index than a true category view

### Scheme C: Make Category the First Tree Layer

The tree would become:

- `category -> level -> generic group -> target`

#### Pros

- strongest category semantics
- very explicit hierarchy

#### Cons

- high implementation risk
- forces broad changes to selection, filtering, restore, and action flows
- makes the tree visually heavier
- conflicts with the current stable root-row assumptions

This is not recommended for the first version.

## Proposed Category File

First version should use a simple JSON file.

Recommended location:

- repository-level default: `new_gui/config/target_categories.json`

Optional future extension:

- run-local override: `<run_dir>/.target_categories.json`

### First-Version Principles

- prefer explicit target lists over pattern-heavy rules
- support ordering and labels
- always provide `All Targets`
- always derive `Uncategorized`
- allow future extension without breaking old files

### Suggested JSON Shape

```json
{
  "version": 1,
  "categories": [
    {
      "id": "timing",
      "label": "Timing",
      "order": 10,
      "targets": [
        "PtTimFuncSSG0p675vOptCtsSxssg0p675v0cTypical100cStpXtiming"
      ]
    },
    {
      "id": "sort",
      "label": "Sort Timing",
      "order": 20,
      "targets": [
        "SortStpRouteFuncSSG0p675vssg0p675v0cGrp"
      ]
    }
  ]
}
```

### Future-Compatible Extensions

These can be added later if needed, but should not be required in version 1:

- `prefixes`
- `patterns`
- `exclude_targets`
- `run_overrides`

## UI Recommendation

Add a left-side navigation rail next to the existing main tree area.

Recommended layout:

- main content row becomes a horizontal layout or splitter
- left side: category navigation widget
- right side: existing tree view

### Left Panel Content

Suggested items:

- `All Targets`
- configured categories in declared order
- `Uncategorized`

Optional metadata display:

- target count per category

### Interaction Model

- single-select only in version 1
- selecting a category rebuilds the right tree using only matching targets
- the right tree keeps the same `level -> generic group -> target` structure
- if no target matches, show an empty-state message in the tree area

## Data-Flow Integration

Current effective path:

1. `run_dependency.parse_dependency_file(...)`
2. `tree_structure.build_level_display_groups(...)`
3. `MainWindow._append_target_groups_to_model(...)`
4. `QTreeView`

Recommended category-aware path:

1. parse dependency targets as today
2. load category definition file
3. resolve selected category into a target-name set
4. filter `targets_by_level` to that target set
5. pass filtered groups into existing display-group builder
6. render tree as today

This keeps category logic outside the tree row model.

## New Modules Recommended

### `new_gui/services/target_categories.py`

Responsibilities:

- load JSON config
- validate schema
- compute ordered category definitions
- resolve category membership for a run
- compute `Uncategorized`

### `new_gui/ui/widgets/category_nav.py`

Responsibilities:

- render the left-side navigation list
- expose category selection signals
- update selected state and counts

### MainWindow / View Controller Changes

Recommended responsibilities:

- store current `category_id`
- rebuild visible tree using category scope
- preserve category selection during run change and refresh
- integrate category scope into restore plan

## State and Restore Rules

This is the most important integration point.

The current restore flow already tracks:

- main
- search
- status
- trace

Category scope should be modeled as an additional axis, not as a replacement mode.

### Recommended Restore Shape

Example:

```json
{
  "mode": "status",
  "status": "failed",
  "category_id": "timing",
  "scroll": 120
}
```

### Rules

- `All Targets` means no category filtering
- category selection should survive run refresh
- category selection should survive status and search filter replay
- if a trace result contains no targets inside the current category, the UI should
  either show an empty scoped trace view or notify and fall back explicitly
- silent fallback should be avoided

## Action Semantics

Category selection should not redefine action semantics by itself.

Version 1 behavior should remain:

- actions are still driven by tree selection
- category only changes what rows are visible
- execute actions still act on selected targets or selected generic group rows

This avoids accidental “run whole category” behavior.

If category-wide batch actions are ever wanted, they should be introduced as a
separate explicit feature later.

## Generic Group Interaction

The recently added synthetic generic group rows should continue to work exactly as
they do today inside category scope:

- default collapsed on expand-all
- group-row batch execute actions
- aggregated group-row status
- leaf-row single-target actions

Category filtering should happen before display grouping, so generic groups only
contain in-scope targets.

## Edge Cases to Define Up Front

### Multi-Category Membership

Recommended first-version rule:

- a target may appear in multiple categories
- category views are independent filtered scopes

This is simpler and more flexible than enforcing one-to-one ownership.

### Uncategorized Targets

Recommended rule:

- any target not matched by any configured category appears in `Uncategorized`

### Missing or Invalid Config

Recommended rule:

- navigation falls back to `All Targets` only
- GUI remains fully usable
- log a warning, do not block startup

## Implementation Difficulty

Overall difficulty: **medium**

### Why Not Low

- left-side layout changes are straightforward
- the real complexity is state coordination:
  - run change
  - search replay
  - status filter replay
  - trace replay
  - scroll restore

### Why Not High

- current tree row semantics can stay intact
- no need to redesign execute or selection logic
- existing grouped-tree pipeline is reusable

## Suggested Delivery Phases

### Phase 1: Config and Navigation Skeleton

- add category config parser
- add left-side navigation UI
- render category list and counts
- keep selection on `All Targets`

### Phase 2: Category-Scoped Tree Rebuild

- apply selected category to tree rebuild
- support `All Targets`
- support `Uncategorized`

### Phase 3: Restore and Filter Integration

- include `category_id` in restore plan
- replay category + search/status/trace together
- preserve scroll position

### Phase 4: UX Refinement

- empty states
- invalid config warnings
- category count badges
- minor styling polish

## Final Recommendation

Proceed with **Scheme A** when work resumes.

It is the strongest option because it delivers the intended readability win while
protecting the existing tree model, execute semantics, and styling behavior that
have already been stabilized.
