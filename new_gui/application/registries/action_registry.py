"""Single-source action registry for top buttons and context-menu actions.

This registry is also the authoritative source for the Executable Agent's
First-Version Action Boundary: every entry here is a Registered GUI Action,
classified as Read-Only or State-Changing per the project CONTEXT.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Literal, Optional, Tuple


ActionCategory = Literal["execute", "file", "trace", "terminal"]


@dataclass(frozen=True)
class UiActionDefinition:
    """Declarative action definition for button, menu, and Agent wiring."""

    action_id: str
    button_label: str
    menu_label: str
    tooltip: str
    trigger: Callable[[object], None]
    preferred_row: Optional[int] = None
    button_style: str = "neutral"
    category: ActionCategory = "execute"
    mutates_state: bool = False
    requires_confirmation: bool = False
    agent_description: str = ""
    requires_selection: bool = True


def _start_action(command: str) -> Callable[[object], None]:
    """Return one action trigger that dispatches to window.start(command)."""
    return lambda window, cmd=command: window.start(cmd)


_ACTION_DEFINITIONS: Tuple[UiActionDefinition, ...] = (
    UiActionDefinition(
        action_id="run_all",
        button_label="Run All",
        menu_label="\u25b6 Run All",
        tooltip="Run all targets (Ctrl+Shift+Enter)",
        trigger=_start_action("XMeta_run all"),
        preferred_row=1,
        button_style="primary",
        category="execute",
        mutates_state=True,
        requires_confirmation=True,
        agent_description="Run every target in the current run directory.",
        requires_selection=False,
    ),
    UiActionDefinition(
        action_id="run",
        button_label="Run",
        menu_label="\u25b6 Run Selected",
        tooltip="Run selected targets (Ctrl+Enter)",
        trigger=_start_action("XMeta_run"),
        preferred_row=1,
        button_style="primary",
        category="execute",
        mutates_state=True,
        requires_confirmation=True,
        agent_description="Run the currently selected targets in dependency order.",
        requires_selection=True,
    ),
    UiActionDefinition(
        action_id="stop",
        button_label="Stop",
        menu_label="\u25a0 Stop",
        tooltip="Stop selected targets",
        trigger=_start_action("XMeta_stop"),
        preferred_row=1,
        button_style="warning",
        category="execute",
        mutates_state=True,
        requires_confirmation=True,
        agent_description="Stop execution for the currently selected targets.",
        requires_selection=True,
    ),
    UiActionDefinition(
        action_id="skip",
        button_label="Skip",
        menu_label="\u25cb Skip",
        tooltip="Skip selected targets",
        trigger=_start_action("XMeta_skip"),
        preferred_row=1,
        button_style="warning",
        category="execute",
        mutates_state=True,
        requires_confirmation=True,
        agent_description="Mark the selected targets as skipped for the next run.",
        requires_selection=True,
    ),
    UiActionDefinition(
        action_id="unskip",
        button_label="Unskip",
        menu_label="\u25cf Unskip",
        tooltip="Unskip selected targets",
        trigger=_start_action("XMeta_unskip"),
        preferred_row=1,
        button_style="neutral",
        category="execute",
        mutates_state=True,
        requires_confirmation=True,
        agent_description="Clear the skipped state on the selected targets.",
        requires_selection=True,
    ),
    UiActionDefinition(
        action_id="invalid",
        button_label="Invalid",
        menu_label="\u2715 Invalid",
        tooltip="Mark selected targets as invalid",
        trigger=_start_action("XMeta_invalid"),
        preferred_row=1,
        button_style="warning",
        category="execute",
        mutates_state=True,
        requires_confirmation=True,
        agent_description="Mark the selected targets as invalid in the run state.",
        requires_selection=True,
    ),
    UiActionDefinition(
        action_id="term",
        button_label="Term",
        menu_label="\u2318 Terminal",
        tooltip="Open the embedded terminal panel in the current run directory",
        trigger=lambda window: window.open_terminal(),
        preferred_row=2,
        button_style="neutral",
        category="terminal",
        mutates_state=False,
        requires_confirmation=False,
        agent_description="Open an embedded terminal panel in the current run directory.",
        requires_selection=False,
    ),
    UiActionDefinition(
        action_id="csh",
        button_label="Csh",
        menu_label="\U0001f4c4 csh",
        tooltip="Open shell file for selected target",
        trigger=lambda window: window.handle_csh(),
        preferred_row=2,
        button_style="neutral",
        category="file",
        mutates_state=False,
        requires_confirmation=False,
        agent_description="Open the csh shell file for the selected target.",
        requires_selection=True,
    ),
    UiActionDefinition(
        action_id="log",
        button_label="Log",
        menu_label="\U0001f4cb Log",
        tooltip="Open log file for selected target",
        trigger=lambda window: window.handle_log(),
        preferred_row=2,
        button_style="neutral",
        category="file",
        mutates_state=False,
        requires_confirmation=False,
        agent_description="Open the log file for the selected target.",
        requires_selection=True,
    ),
    UiActionDefinition(
        action_id="cmd",
        button_label="Cmd",
        menu_label="\u26a1 cmd",
        tooltip="Open command file for selected target",
        trigger=lambda window: window.handle_cmd(),
        preferred_row=2,
        button_style="neutral",
        category="file",
        mutates_state=False,
        requires_confirmation=False,
        agent_description="Open the command file for the selected target.",
        requires_selection=True,
    ),
    UiActionDefinition(
        action_id="trace_up",
        button_label="Trace Up",
        menu_label="\u2b06 Trace Up (Ctrl+U)",
        tooltip="Trace upstream dependencies",
        trigger=lambda window: window.retrace_tab("in"),
        preferred_row=2,
        button_style="neutral",
        category="trace",
        mutates_state=False,
        requires_confirmation=False,
        agent_description="Trace upstream dependencies for the selected target.",
        requires_selection=True,
    ),
    UiActionDefinition(
        action_id="trace_down",
        button_label="Trace Down",
        menu_label="\u2b07 Trace Down (Ctrl+D)",
        tooltip="Trace downstream dependencies",
        trigger=lambda window: window.retrace_tab("out"),
        preferred_row=2,
        button_style="neutral",
        category="trace",
        mutates_state=False,
        requires_confirmation=False,
        agent_description="Trace downstream dependencies for the selected target.",
        requires_selection=True,
    ),
)

_ACTIONS_BY_ID: Dict[str, UiActionDefinition] = {
    definition.action_id: definition for definition in _ACTION_DEFINITIONS
}


def get_action_definition(action_id: str) -> UiActionDefinition:
    """Return one action definition by id."""
    return _ACTIONS_BY_ID[action_id]


def get_all_action_definitions() -> Tuple[UiActionDefinition, ...]:
    """Return every Registered GUI Action definition in declared order."""
    return _ACTION_DEFINITIONS


def get_top_button_action_ids() -> Tuple[str, ...]:
    """Return top-button action ids in stable display order."""
    return tuple(
        definition.action_id
        for definition in _ACTION_DEFINITIONS
        if definition.preferred_row in (1, 2)
    )


def get_top_button_choices() -> List[Tuple[str, str]]:
    """Return top-button ids and labels for the visibility picker."""
    return [
        (definition.action_id, definition.button_label)
        for definition in _ACTION_DEFINITIONS
        if definition.preferred_row in (1, 2)
    ]


def get_top_button_definitions() -> Tuple[UiActionDefinition, ...]:
    """Return all top-button definitions with row and style metadata."""
    return tuple(
        definition
        for definition in _ACTION_DEFINITIONS
        if definition.preferred_row in (1, 2)
    )


def get_execute_menu_action_ids() -> Tuple[str, ...]:
    """Return execute-menu action ids in display order."""
    return ("run_all", "run", "stop", "skip", "unskip", "invalid")


def get_file_menu_action_ids() -> Tuple[str, ...]:
    """Return file-menu action ids in display order."""
    return ("term", "csh", "log", "cmd")


def get_trace_menu_action_ids() -> Tuple[str, ...]:
    """Return trace-menu action ids in display order."""
    return ("trace_up", "trace_down")
