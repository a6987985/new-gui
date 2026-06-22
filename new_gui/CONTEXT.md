# XMeta Console GUI Context

XMeta Console GUI is a desktop operations console for tracking and acting on EDA run targets.
This context captures product language for the planned built-in AI execution capability.

## Language

**Executable Agent**:
An AI-assisted operator that can propose and perform actions inside the console workflow.
_Avoid_: Chatbot, passive assistant

**Registered GUI Action**:
An operation already exposed by the console UI and backed by existing application behavior.
_Avoid_: Hidden shell command, arbitrary operation

**First-Version Action Boundary**:
The first release scope that limits the **Executable Agent** to **Registered GUI Actions**.
_Avoid_: Full shell access, unrestricted automation

**Read-Only Action**:
A **Registered GUI Action** that inspects, opens, filters, or navigates console information without changing run state.
_Avoid_: Safe command, harmless operation

**State-Changing Action**:
A **Registered GUI Action** that can modify run state, target state, files, or execution.
_Avoid_: Automatic mutation, silent operation

**User Confirmation**:
An explicit user approval required before the **Executable Agent** performs a **State-Changing Action**.
_Avoid_: Silent approval, implied consent

## Relationships

- The **Executable Agent** belongs to the XMeta Console GUI operations workflow
- The **Executable Agent** can perform **Registered GUI Actions** within the **First-Version Action Boundary**
- A **Registered GUI Action** is either a **Read-Only Action** or a **State-Changing Action**
- A **State-Changing Action** requires **User Confirmation**

## Example Dialogue

> **Dev:** "Should the built-in AI only explain what it sees?"
> **Domain expert:** "No. The first planned capability is an **Executable Agent** that can act inside the console workflow."
> **Dev:** "Can it generate and run shell commands in the first version?"
> **Domain expert:** "No. The **First-Version Action Boundary** limits execution to **Registered GUI Actions**."
> **Dev:** "Does every action need a confirmation dialog?"
> **Domain expert:** "No. A **Read-Only Action** can run directly, but a **State-Changing Action** requires **User Confirmation**."

## Flagged Ambiguities

- "AI Agent" could mean a passive assistant, a recommendation tool, or an execution-capable operator. Resolved: this project means **Executable Agent**.
- "Executable" could mean arbitrary shell execution or existing UI actions. Resolved: first version means **Registered GUI Actions** only.
- "Confirm actions" could mean every interaction or only risky changes. Resolved: only **State-Changing Actions** require **User Confirmation**.

## Implementation Anchors

- The **Registered GUI Action** catalog and its agent metadata live in
  `new_gui/application/registries/action_registry.py`. Every entry there is
  the single source of truth for what an **Executable Agent** is allowed to do
  in the first version.
- The **Executable Agent** layer is `new_gui/application/agent/`:
  - `action_catalog.py` exposes the LLM-visible projection.
  - `agent_context.py` and `agent_context_snapshot.py` capture the read-only
    `AgentSessionContext` consumed by planners.
  - `agent_planner.py` defines the swappable planner protocol; `RulePlanner`
    is the deterministic placeholder used until an LLM is wired in.
  - `agent_executor.py` enforces the **First-Version Action Boundary** and the
    **User Confirmation** invariant.
- The Qt-side integration lives in
  `new_gui/presentation/presenters/agent_controller.py` and
  `new_gui/presentation/views/widgets/agent_panel.py`. The dock is mounted by
  `MainWindow._install_agent_dock` and toggled from the `Agent` menu.

## Second-Version Action Boundary

The first-version boundary kept every action parameter-free. The second-version
boundary lets the Agent target a specific subset of targets while keeping the
catalog as the only execution path:

- Only the execute actions ``run / stop / skip / unskip / invalid`` accept a
  ``targets`` parameter (see ``agent_parameters.supports_targets_parameter``).
- Requested targets must already appear in the user-visible scope captured by
  ``AgentSessionContext.visible_targets``; out-of-scope targets are rejected.
- ``AgentExecutor`` projects the requested targets onto the live window
  selection through ``window._select_targets_in_tree`` before firing the
  existing UI trigger, so the GUI flow stays identical.

## Audit and Planner Pluggability

- ``AgentAuditLog`` writes one JSON object per Agent interaction to
  ``.agent/agent_audit.log`` by default. The dock auto-installs it unless the
  filesystem rejects the path.
- Planners implement the ``AgentPlanner`` protocol. ``RulePlanner`` ships as
  the offline default. ``LLMPlanner`` reuses the OpenAI chat-completion
  protocol and gracefully falls back to ``RulePlanner`` when no API key is
  configured or the HTTP call fails.
- LLM configuration is taken from ``NEW_GUI_AGENT_API_KEY`` /
  ``NEW_GUI_AGENT_API_BASE`` / ``NEW_GUI_AGENT_MODEL`` (with ``OPENAI_API_KEY``
  as a final fallback), so deployments can stay air-gapped by default.

## Feedback Loop

The Agent does not just fire actions and forget. Around every prompt the
``AgentController`` collects a coarse :class:`RunStateObservation` (current
run + status counts + selected targets) before and after execution and
records the resulting ``ObservationDiff`` to:

- ``AgentInteractionRecord`` for the in-process history,
- the dock transcript (`status delta`, selection +/-, run changed), and
- the persisted audit JSONL under ``observation``.

This is the substrate a future LLM planner can read to react to "did the
last run change anything", without anyone breaking the Agent boundary.

## Multi-Step Loop

Some intents need more than one action: inspect, then act, then re-inspect.
``MultiStepAgentLoop`` wraps the controller and re-plans between actions:

- It calls ``controller.submit_prompt`` once per iteration.
- After each successful step it appends the observed ``ObservationDiff`` to
  the next iteration's prompt as ``[loop iteration N]`` continuation.
- The loop stops when the planner returns no steps, when the observation
  diff is empty (no state change), or when ``max_iterations`` is reached.

This keeps the boundary unchanged: every action still flows through
``AgentExecutor`` and ``ConfirmationGate``.

## Audit UI

The Agent dock now ships a ``History`` tab that loads
``.agent/agent_audit.log`` through :mod:`agent_audit_reader`:

- ``summarize_records`` returns prompt/action counts and per-action_id totals
  for governance reviews.
- ``format_audit_records`` renders a compact tail (default 50 lines) with
  status deltas surfaced inline.
- The reader is permissive: malformed lines are skipped instead of raising,
  so a partial write never breaks the dock.
