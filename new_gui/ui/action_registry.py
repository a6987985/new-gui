"""Single-source action registry for top buttons and context-menu actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class UiActionDefinition:
    """Declarative action definition for button and menu wiring."""

    action_id: str
    button_label: str
    menu_label: str
    tooltip: str
    trigger: Callable[[object], None]
    preferred_row: Optional[int] = None
    button_style: str = "neutral"


def _start_action(command: str) -> Callable[[object], None]:
    """Return one action trigger that dispatches to window.start(command)."""
    return lambda window, cmd=command: window.start(cmd)


_ACTION_DEFINITIONS: Tuple[UiActionDefinition, ...] = (
    UiActionDefinition(
        action_id="run_all",
        button_label="Run All",
        menu_label="▶ Run All",
        tooltip="Run all targets (Ctrl+Shift+Enter)",
        trigger=_start_action("XMeta_run all"),
        preferred_row=1,
        button_style="primary",
    ),
    UiActionDefinition(
        action_id="run",
        button_label="Run",
        menu_label="▶ Run Selected",
        tooltip="Run selected targets (Ctrl+Enter)",
        trigger=_start_action("XMeta_run"),
        preferred_row=1,
        button_style="primary",
    ),
    UiActionDefinition(
        action_id="stop",
        button_label="Stop",
        menu_label="■ Stop",
        tooltip="Stop selected targets",
        trigger=_start_action("XMeta_stop"),
        preferred_row=1,
        button_style="warning",
    ),
    UiActionDefinition(
        action_id="skip",
        button_label="Skip",
        menu_label="○ Skip",
        tooltip="Skip selected targets",
        trigger=_start_action("XMeta_skip"),
        preferred_row=1,
        button_style="warning",
    ),
    UiActionDefinition(
        action_id="unskip",
        button_label="Unskip",
        menu_label="● Unskip",
        tooltip="Unskip selected targets",
        trigger=_start_action("XMeta_unskip"),
        preferred_row=1,
        button_style="neutral",
    ),
    UiActionDefinition(
        action_id="invalid",
        button_label="Invalid",
        menu_label="✕ Invalid",
        tooltip="Mark selected targets as invalid",
        trigger=_start_action("XMeta_invalid"),
        preferred_row=1,
        button_style="warning",
    ),
    UiActionDefinition(
        action_id="term",
        button_label="Term",
        menu_label="⌘ Terminal",
        tooltip="Open the embedded terminal panel in the current run directory",
        trigger=lambda window: window.open_terminal(),
        preferred_row=2,
        button_style="neutral",
    ),
    UiActionDefinition(
        action_id="csh",
        button_label="Csh",
        menu_label="📄 csh",
        tooltip="Open shell file for selected target",
        trigger=lambda window: window.handle_csh(),
        preferred_row=2,
        button_style="neutral",
    ),
    UiActionDefinition(
        action_id="log",
        button_label="Log",
        menu_label="📋 Log",
        tooltip="Open log file for selected target",
        trigger=lambda window: window.handle_log(),
        preferred_row=2,
        button_style="neutral",
    ),
    UiActionDefinition(
        action_id="cmd",
        button_label="Cmd",
        menu_label="⚡ cmd",
        tooltip="Open command file for selected target",
        trigger=lambda window: window.handle_cmd(),
        preferred_row=2,
        button_style="neutral",
    ),
    UiActionDefinition(
        action_id="trace_up",
        button_label="Trace Up",
        menu_label="⬆ Trace Up (Ctrl+U)",
        tooltip="Trace upstream dependencies",
        trigger=lambda window: window.retrace_tab("in"),
        preferred_row=2,
        button_style="neutral",
    ),
    UiActionDefinition(
        action_id="trace_down",
        button_label="Trace Down",
        menu_label="⬇ Trace Down (Ctrl+D)",
        tooltip="Trace downstream dependencies",
        trigger=lambda window: window.retrace_tab("out"),
        preferred_row=2,
        button_style="neutral",
    ),
)

_ACTIONS_BY_ID: Dict[str, UiActionDefinition] = {
    definition.action_id: definition for definition in _ACTION_DEFINITIONS
}


def get_action_definition(action_id: str) -> UiActionDefinition:
    """Return one action definition by id."""
    return _ACTIONS_BY_ID[action_id]


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
