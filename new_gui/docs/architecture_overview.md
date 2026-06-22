# XMeta Console GUI Architecture Overview

> Last Updated: 2026-06-22

## Layer Overview

The codebase is organized as a package under `new_gui/` with clear runtime responsibilities:

- `main.py`: PyQt application entry and `MainWindow` integration surface
- `presentation/`: widgets, dialogs, builders, styles, theme logic, and presenter flows
- `presentation/state/`: window-owned state containers used to reduce `MainWindow` field sprawl
- `application/`: use-case orchestration and action-level workflow logic
- `model/services/`: view-state rules, tree-state helpers, navigation logic, and UI-adjacent domain behavior
- `infrastructure/repositories/`: filesystem, dependency parsing, shell integration, status/tune repositories
- `shared/config/`: settings, constants, regexes, and shared logger setup

## Recent Refactor Highlights

### 1. Window State Consolidation

`MainWindow` no longer defines all runtime fields inline as unrelated attributes.

Key state containers:

- `presentation/state/window_state.py`
  - `RunCacheState`
  - `ViewState`
  - `RuntimeState`
  - `SidebarState`
  - `WindowStateStore`

This makes state ownership more explicit and reduces future risk when splitting `MainWindow` behavior further.

### 2. Central Cache Management

`infrastructure/repositories/run_cache_manager.py` centralizes cache invalidation and cache writes for:

- target/status caches
- tune-file caches
- BSUB-parameter caches
- collapsible target group caches

This removes duplicated cache-reset logic from scattered presenter paths.

### 3. Presenter Flow Splitting

Large view orchestration responsibilities were split out of `presentation/presenters/view_controller.py` into focused modules:

- `presentation/presenters/view_filter_controller.py`
  - search filtering
  - trace filtering
  - close/restore filtered view transitions
- `presentation/presenters/view_run_controller.py`
  - active-run refresh
  - dependency-triggered tree rebuild

`view_controller.py` remains as a compatibility entry point and orchestration surface, while high-churn flows now live in narrower modules.

### 4. Dependency Parsing Split

`infrastructure/repositories/run_dependency.py` was reduced to a compatibility re-export layer.

Focused modules now own the real logic:

- `infrastructure/repositories/run_dependency_parser.py`
  - dependency file parsing
  - active target extraction
  - collapsible generic group parsing
- `infrastructure/repositories/run_dependency_query.py`
  - trace lookups
  - grouped dependency graph building
  - retrace target queries

This improves discoverability and makes the dependency layer easier to test incrementally.


### 5. Executable Agent Integration

The Executable Agent is a self-contained surface layered on top of the
existing presenter and action stack. It never bypasses the registered GUI
action layer.

Top-level layout:

- `application/agent/`: planning, parameter validation, execution, audit,
  observation, and multi-step loop
- `presentation/presenters/agent_controller.py`: glue between the panel and
  the application package
- `presentation/views/widgets/agent_panel.py`: Qt dock widget used to drive
  the Agent from the UI
- `main.py`: wires `AgentController` and `AgentPanel` into a hidden
  right-side `QDockWidget`, toggled from the `Agent` menu (`Ctrl+Shift+A`)

Key modules in `application/agent/`:

- `action_catalog.py`: exposes Registered GUI Actions as the only callable
  surface available to the Agent
- `agent_context.py` / `agent_context_snapshot.py`: build read-only session
  snapshots from `MainWindow` so planners cannot mutate runtime state
- `agent_parameters.py`: typed parameter validation, including the
  optional `targets` projection used by the Second-Version Boundary
- `agent_planner.py`: defines `AgentPlanStep` and the rule-based
  `RulePlanner` fallback
- `agent_llm.py`: `LLMPlanner` with `LLMPlannerSettings.from_env()`,
  injectable HTTP fetcher, and automatic fallback to the rule planner
- `agent_executor.py`: enforces both Action Boundaries, applies parameter
  projection, and routes State-Changing Actions through a
  `ConfirmationGate` (Qt builds a real `QMessageBox` via
  `qt_confirmation_gate`)
- `agent_observation.py`: collects `RunStateObservation` before and after
  each step and computes a structured `ObservationDiff`
- `agent_audit.py` / `agent_audit_reader.py`: append-only JSONL audit log
  at `default_audit_log_path()` (`.agent/agent_audit.log`) with a separate
  offline reader and summary helper
- `agent_loop.py`: `MultiStepAgentLoop` wrapping the controller for
  iterative planning runs, capturing per-turn records

Invariants enforced by this layer:

- The Agent can only call actions present in
  `application/registries/action_registry.py`; unknown actions raise
  `AgentExecutionError`
- State-Changing Actions cannot fire without a positive
  `ConfirmationDecision` from the gate
- Parameter payloads are validated before any UI trigger runs
- Every prompt, plan step, execution result, and observation diff is
  recorded in the audit log when one is configured

Test coverage lives under `tests/test_agent_*.py` (7 modules) and exercises
the action boundary, parameters, audit log, observation loop, controller
flow, multi-step loop, and panel theming. The current suite reports
88 passing tests.

## Maintenance Guidance

### Stable Boundaries

Prefer keeping these boundaries stable:

- `presentation/views/*`: visual widget and builder code only
- `presentation/presenters/*`: Qt event orchestration and UI workflow only
- `model/services/*`: pure state or transformation logic with minimal widget knowledge
- `infrastructure/repositories/*`: file/process/external environment access only

### Recommended Next Steps

High-value next refactors, if needed:

1. Continue shrinking `main.py` by moving startup wiring into a bootstrap module
2. Introduce a thin application facade so presenters call `application/` instead of touching repositories directly
3. Add targeted tests around cache invalidation and dependency rebuild flows
4. Keep new compatibility layers small and temporary
5. Extend `application/agent/` planners (e.g. retrieval-augmented prompts) without weakening the action registry boundary

## Removed Legacy Shells

The old placeholder package shells were removed because they no longer reflected the real module layout:

- `ui/`
- `services/`
- `config/`
- `domain/entities/`

The canonical structure is now the package tree under `new_gui/`.
