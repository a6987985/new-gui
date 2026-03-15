"""Dependency parsing and dependency-graph helpers."""

import os
import re
from collections import deque
from typing import Deque, Dict, List, Optional

from new_gui.config.settings import (
    RE_ACTIVE_TARGETS,
    RE_ALL_RELATED,
    RE_DEPENDENCY_OUT,
    RE_LEVEL_LINE,
    logger,
)
from new_gui.services.run_status import build_status_cache, get_target_status


TargetsByLevel = Dict[int, List[str]]
DependencyGraph = Dict[str, object]
TraceLookup = Dict[str, List[str]]
TraceTargets = Dict[str, TraceLookup]
CollapsibleTargetGroups = Dict[str, List[str]]


RE_INSTANCES_LIST_LINE = re.compile(r'^set\s+INSTANCES_LIST_([A-Za-z0-9_]+)\s*=\s*"([^"]*)"')
COLLAPSIBLE_GROUP_MARKER = "Generic"
MIN_COLLAPSIBLE_GROUP_SIZE = 3


def parse_dependency_file(run_base_dir: str, run_name: str) -> TargetsByLevel:
    """Parse .target_dependency.csh into a level-to-target mapping."""
    dependency_file = os.path.join(run_base_dir, run_name, ".target_dependency.csh")
    targets_by_level: TargetsByLevel = {}

    if not os.path.exists(dependency_file):
        logger.warning(f"Dependency file not found for {run_name}")
        return targets_by_level

    try:
        with open(dependency_file, "r") as handle:
            for line in handle:
                line = line.strip()
                match = RE_LEVEL_LINE.match(line)
                if match:
                    level_num = int(match.group(1))
                    targets = match.group(2).split()
                    targets_by_level[level_num] = targets
    except FileNotFoundError:
        logger.warning(f"Dependency file not found: {dependency_file}")
    except PermissionError as exc:
        logger.error(f"Permission denied reading dependency file: {exc}")
    except UnicodeDecodeError as exc:
        logger.error(f"Error decoding dependency file: {exc}")
    except Exception as exc:
        logger.error(f"Error parsing dependency file for {run_name}: {exc}")

    return targets_by_level


def get_active_targets(run_dir: str) -> List[str]:
    """Parse ACTIVE_TARGETS from .target_dependency.csh."""
    if not run_dir:
        return []

    deps_file = os.path.join(run_dir, ".target_dependency.csh")
    if not os.path.exists(deps_file):
        return []

    try:
        with open(deps_file, "r") as handle:
            content = handle.read()
        match = RE_ACTIVE_TARGETS.search(content)
        if match:
            return match.group(1).split()
    except FileNotFoundError:
        logger.warning(f"Dependency file not found: {deps_file}")
    except PermissionError as exc:
        logger.error(f"Permission denied reading dependency file: {exc}")
    except UnicodeDecodeError as exc:
        logger.error(f"Error decoding dependency file: {exc}")
    except Exception as exc:
        logger.error(f"Unexpected error reading ACTIVE_TARGETS: {exc}")
    return []


def _read_dependency_content(dependency_file: str) -> str:
    """Return dependency file contents or an empty string when unavailable."""
    if not os.path.exists(dependency_file):
        return ""

    try:
        with open(dependency_file, "r") as handle:
            return handle.read()
    except FileNotFoundError:
        logger.warning(f"Dependency file not found: {dependency_file}")
    except PermissionError as exc:
        logger.error(f"Permission denied reading dependency file: {exc}")
    except UnicodeDecodeError as exc:
        logger.error(f"Error decoding dependency file: {exc}")
    except Exception as exc:
        logger.error(f"Unexpected error reading dependency file: {exc}")
    return ""


def _list_all_targets(targets_by_level: TargetsByLevel) -> List[str]:
    """Flatten level groups into a stable target list."""
    all_targets: List[str] = []
    for level in sorted(targets_by_level.keys()):
        all_targets.extend(targets_by_level.get(level) or [])
    return all_targets


def _dedupe_targets(targets: List[str]) -> List[str]:
    """Return targets with duplicates removed while preserving order."""
    seen = set()
    ordered_targets: List[str] = []
    for target in targets:
        if not target or target in seen:
            continue
        seen.add(target)
        ordered_targets.append(target)
    return ordered_targets


def _normalize_collapsible_group_label(raw_group_name: str) -> str:
    """Return the display label used for a collapsible target group."""
    normalized_group_name = raw_group_name or ""
    for prefix in ("TIMING_", "SORTTIMING_"):
        if normalized_group_name.startswith(prefix):
            normalized_group_name = normalized_group_name[len(prefix):]
            break
    return normalized_group_name.replace("_", "")


def parse_collapsible_target_groups(run_base_dir: str, run_name: str) -> CollapsibleTargetGroups:
    """Parse large generic instance lists into display-group mappings."""
    dependency_file = os.path.join(run_base_dir, run_name, ".target_dependency.csh")
    collapsible_groups: CollapsibleTargetGroups = {}

    content = _read_dependency_content(dependency_file)
    if not content:
        return collapsible_groups

    for line in content.splitlines():
        match = RE_INSTANCES_LIST_LINE.match(line.strip())
        if not match:
            continue

        raw_group_name, members_text = match.groups()
        if COLLAPSIBLE_GROUP_MARKER not in raw_group_name:
            continue

        member_targets = _dedupe_targets(members_text.split())
        if len(member_targets) < MIN_COLLAPSIBLE_GROUP_SIZE:
            continue

        display_label = _normalize_collapsible_group_label(raw_group_name)
        if not display_label:
            continue

        collapsible_groups[display_label] = member_targets

    return collapsible_groups


def _build_direct_downstream_map(content: str, all_targets: List[str]) -> TraceLookup:
    """Parse direct downstream edges from dependency content."""
    all_targets_set = set(all_targets)
    direct_downstream: TraceLookup = {target: [] for target in all_targets}

    for match in RE_DEPENDENCY_OUT.finditer(content):
        source = match.group(1)
        if source not in all_targets_set:
            continue
        direct_targets = [
            target
            for target in match.group(2).strip().split()
            if target in all_targets_set and target != source
        ]
        direct_downstream[source].extend(direct_targets)

    for target in all_targets:
        direct_downstream[target] = _dedupe_targets(direct_downstream.get(target, []))

    return direct_downstream


def _build_explicit_upstream_map(content: str, all_targets: List[str]) -> TraceLookup:
    """Parse explicit upstream closure data from dependency content."""
    all_targets_set = set(all_targets)
    explicit_upstream: TraceLookup = {target: [] for target in all_targets}

    for match in RE_ALL_RELATED.finditer(content):
        target = match.group(1)
        if target not in all_targets_set:
            continue
        upstream_targets = [
            upstream
            for upstream in match.group(2).strip().split()
            if upstream in all_targets_set and upstream != target
        ]
        explicit_upstream[target].extend(upstream_targets)

    for target in all_targets:
        explicit_upstream[target] = _dedupe_targets(explicit_upstream.get(target, []))

    return explicit_upstream


def _build_reverse_map(adjacency: TraceLookup, all_targets: List[str]) -> TraceLookup:
    """Return the reverse adjacency map for the given dependency graph."""
    reverse_map: TraceLookup = {target: [] for target in all_targets}

    for source, downstream_targets in adjacency.items():
        for downstream_target in downstream_targets:
            if downstream_target in reverse_map:
                reverse_map[downstream_target].append(source)

    for target in all_targets:
        reverse_map[target] = _dedupe_targets(reverse_map.get(target, []))

    return reverse_map


def _collect_reachable_targets(start_target: str, adjacency: TraceLookup) -> List[str]:
    """Return all targets reachable from the starting target using BFS order."""
    ordered_targets: List[str] = []
    visited = set()
    queue: Deque[str] = deque(adjacency.get(start_target, []))

    while queue:
        target = queue.popleft()
        if not target or target == start_target or target in visited:
            continue
        visited.add(target)
        ordered_targets.append(target)
        queue.extend(adjacency.get(target, []))

    return ordered_targets


def _build_trace_targets_from_content(content: str, all_targets: List[str]) -> TraceTargets:
    """Build canonical trace targets for both upstream and downstream views."""
    upstream_targets: TraceLookup = {target: [] for target in all_targets}
    downstream_targets: TraceLookup = {target: [] for target in all_targets}
    if not all_targets:
        return {
            "upstream": upstream_targets,
            "downstream": downstream_targets,
        }

    direct_downstream = _build_direct_downstream_map(content, all_targets)
    reverse_direct = _build_reverse_map(direct_downstream, all_targets)
    explicit_upstream = _build_explicit_upstream_map(content, all_targets)

    for target in all_targets:
        fallback_upstream = _collect_reachable_targets(target, reverse_direct)
        upstream_targets[target] = _dedupe_targets(
            explicit_upstream.get(target, []) + fallback_upstream
        )

    for target, upstream_list in upstream_targets.items():
        for upstream_target in upstream_list:
            if upstream_target in downstream_targets:
                downstream_targets[upstream_target].append(target)

    for target in all_targets:
        fallback_downstream = _collect_reachable_targets(target, direct_downstream)
        downstream_targets[target] = _dedupe_targets(
            downstream_targets.get(target, []) + fallback_downstream
        )

    return {
        "upstream": upstream_targets,
        "downstream": downstream_targets,
    }


def build_dependency_trace_targets(run_base_dir: str, run_name: str) -> TraceTargets:
    """Build canonical trace targets for a run from .target_dependency.csh."""
    dependency_file = os.path.join(run_base_dir, run_name, ".target_dependency.csh")
    if not os.path.exists(dependency_file):
        logger.warning(f"Dependency file not found for {run_name}")
        return {"upstream": {}, "downstream": {}}

    targets_by_level = parse_dependency_file(run_base_dir, run_name)
    all_targets = _list_all_targets(targets_by_level)
    content = _read_dependency_content(dependency_file)
    return _build_trace_targets_from_content(content, all_targets)


def get_retrace_targets(run_dir: str, target: str, inout: str) -> List[str]:
    """Return canonical trace targets for the given direction."""
    if not run_dir:
        return []

    normalized_run_dir = run_dir.rstrip(os.sep)
    run_base_dir = os.path.dirname(normalized_run_dir)
    run_name = os.path.basename(normalized_run_dir)
    trace_targets = build_dependency_trace_targets(run_base_dir, run_name)
    direction_key = "upstream" if inout == "in" else "downstream"
    return list(trace_targets.get(direction_key, {}).get(target, []))


def build_dependency_graph(
    run_base_dir: str,
    run_name: str,
    status_cache: Optional[Dict[str, object]] = None,
) -> DependencyGraph:
    """Build dependency graph data and canonical trace targets from .target_dependency.csh."""
    graph_data: DependencyGraph = {
        "nodes": [],
        "edges": [],
        "levels": {},
        "trace_targets": {"upstream": {}, "downstream": {}},
    }

    dep_file = os.path.join(run_base_dir, run_name, ".target_dependency.csh")
    if not os.path.exists(dep_file):
        logger.warning(f"Dependency file not found for {run_name}")
        return graph_data

    try:
        targets_by_level = parse_dependency_file(run_base_dir, run_name)
        graph_data["levels"] = targets_by_level

        all_targets = _list_all_targets(targets_by_level)

        effective_cache = status_cache
        if not effective_cache or effective_cache.get("run") != run_name:
            effective_cache = build_status_cache(run_base_dir, run_name)

        for target in all_targets:
            status = get_target_status(run_base_dir, run_name, target, effective_cache)
            graph_data["nodes"].append((target, status))

        content = _read_dependency_content(dep_file)
        direct_downstream = _build_direct_downstream_map(content, all_targets)
        graph_data["trace_targets"] = _build_trace_targets_from_content(content, all_targets)
        for source in all_targets:
            for downstream in direct_downstream.get(source, []):
                graph_data["edges"].append((source, downstream))
    except Exception as exc:
        logger.error(f"Error building dependency graph: {exc}")

    return graph_data
