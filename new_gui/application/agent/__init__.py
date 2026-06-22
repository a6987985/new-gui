"""Executable Agent integration surface.

This package is the only place where Agent-driven flows live. It depends on
:mod:`new_gui.application.registries.action_registry` as the single source of
truth for Registered GUI Actions and never bypasses it.
"""

from new_gui.application.agent.action_catalog import (
    AgentActionEntry,
    build_action_catalog,
    catalog_as_dict,
)
from new_gui.application.agent.agent_audit import (
    AgentAuditEntry,
    AgentAuditLog,
    default_audit_log_path,
)
from new_gui.application.agent.agent_context import (
    AgentSessionContext,
    snapshot_session_context,
)
from new_gui.application.agent.agent_context_snapshot import snapshot_from_window
from new_gui.application.agent.agent_executor import (
    AgentExecutionError,
    AgentExecutionResult,
    AgentExecutor,
    ConfirmationGate,
    ConfirmationDecision,
)
from new_gui.application.agent.agent_audit_reader import (
    AuditRecord,
    load_audit_file,
    parse_audit_lines,
    summarize_records,
)
from new_gui.application.agent.agent_llm import (
    LLMPlanner,
    LLMPlannerSettings,
)
from new_gui.application.agent.agent_loop import (
    MultiStepAgentLoop,
    MultiStepRunRecord,
    MultiStepTurnRecord,
)
from new_gui.application.agent.agent_observation import (
    ObservationCollector,
    ObservationDiff,
    RunStateObservation,
    default_collector,
    diff_observations,
)
from new_gui.application.agent.agent_parameters import (
    ActionParameterError,
    AgentActionParameters,
    supports_targets_parameter,
    validate_action_parameters,
)
from new_gui.application.agent.agent_planner import (
    AgentPlanStep,
    AgentPlanner,
    RulePlanner,
)
from new_gui.application.agent.agent_claude import (
    ClaudeAgentPlanner,
    ClaudePlannerSettings,
)
from new_gui.application.agent.agent_backend import (
    BACKEND_CLAUDE,
    BACKEND_OPENAI,
    BACKEND_RULE,
    SUPPORTED_BACKENDS,
    build_planner,
    resolve_backend,
)

__all__ = [
    "ActionParameterError",
    "AgentActionEntry",
    "AgentActionParameters",
    "AgentAuditEntry",
    "AgentAuditLog",
    "AgentExecutionError",
    "AgentExecutionResult",
    "AgentExecutor",
    "AgentPlanStep",
    "AgentPlanner",
    "AgentSessionContext",
    "ConfirmationDecision",
    "ConfirmationGate",
    "AuditRecord",
    "LLMPlanner",
    "LLMPlannerSettings",
    "MultiStepAgentLoop",
    "MultiStepRunRecord",
    "MultiStepTurnRecord",
    "ObservationCollector",
    "ObservationDiff",
    "RulePlanner",
    "RunStateObservation",
    "build_action_catalog",
    "catalog_as_dict",
    "default_audit_log_path",
    "default_collector",
    "diff_observations",
    "load_audit_file",
    "parse_audit_lines",
    "summarize_records",
    "snapshot_from_window",
    "snapshot_session_context",
    "supports_targets_parameter",
    "validate_action_parameters",
    "ClaudeAgentPlanner",
    "ClaudePlannerSettings",
    "BACKEND_CLAUDE",
    "BACKEND_OPENAI",
    "BACKEND_RULE",
    "SUPPORTED_BACKENDS",
    "build_planner",
    "resolve_backend",
]
