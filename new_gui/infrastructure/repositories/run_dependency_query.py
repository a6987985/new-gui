"""Dependency graph and trace-query helpers."""

from __future__ import annotations

import os
import re
from collections import deque
from typing import Callable, Deque, Dict, List, Optional

from new_gui.infrastructure.repositories.run_dependency_parser import (
    GRAPH_GROUP_PREFIX,
    TargetsByLevel,
    CollapsibleTargetGroups,
    dedupe_targets,
    list_all_targets,
    parse_collapsible_target_groups,
    parse_dependency_file,
    read_dependency_content,
)
from new_gui.infrastructure.repositories.run_status import build_status_cache, get_target_status
from new_gui.shared.config.settings import RE_ALL_RELATED, RE_DEPENDENCY_OUT, logger


DependencyGraph = Dict[str, object]
TraceLookup = Dict[str, List[str]]
TraceTargets = Dict[str, TraceLookup]
NodeMeta = Dict[str, Dict[str, object]]
GROUP_STATUS_PRIORITY = ["failed", "pending", "running", "scheduled", "skip", "finish", ""]


def _find_named_target_assignment(pattern: re.Pattern, content: str, target: str):
    """Return the regex match for a named target assignment."""
    for match in pattern.finditer(content):
        if match.group(1) == target:
            return match
    return None


def _direction_key(inout: str) -> str:
    """Normalize trace direction aliases to canonical keys."""
    if inout in ("in", "up", "upstream"):
        return "upstream"
    return "downstream"


def build_direct_downstream_map(content: str, all_targets: List[str]) -> TraceLookup:
    """Return a direct-downstream lookup extracted from dependency content."""
    direct_downstream: TraceLookup = {target: [] for target in all_targets}
    for target in all_targets:
        match = _find_named_target_assignment(RE_DEPENDENCY_OUT, content, target)
        if not match:
            continue
        direct_downstream[target] = dedupe_targets(match.group(2).split())
    return direct_downstream


def _reverse_direct_map(direct_downstream: TraceLookup, all_targets: List[str]) -> TraceLookup:
    """Return a direct-upstream lookup from direct downstream edges."""
    direct_upstream: TraceLookup = {target: [] for target in all_targets}
    known_targets = set(all_targets)
    for source, downstream_targets in direct_downstream.items():
        for downstream_target in downstream_targets:
            if downstream_target not in known_targets:
                continue
            direct_upstream.setdefault(downstream_target, []).append(source)
    return {
        target: dedupe_targets(upstream_targets)
        for target, upstream_targets in direct_upstream.items()
    }


def _collect_reachable_targets(start_target: str, adjacency: TraceLookup) -> List[str]:
    """Return all targets reachable from one target through an adjacency map."""
    reachable_targets: List[str] = []
    visited = {start_target}
    queue: Deque[str] = deque(adjacency.get(start_target, []))

    while queue:
        current_target = queue.popleft()
        if current_target in visited:
            continue
        visited.add(current_target)
        reachable_targets.append(current_target)
        queue.extend(adjacency.get(current_target, []))

    return reachable_targets


def _build_trace_targets_from_edges(content: str, all_targets: List[str]) -> TraceTargets:
    """Build transitive upstream/downstream trace targets from direct edges."""
    direct_downstream = build_direct_downstream_map(content, all_targets)
    direct_upstream = _reverse_direct_map(direct_downstream, all_targets)
    target_order = {target: index for index, target in enumerate(all_targets)}

    def order_targets(targets: List[str]) -> List[str]:
        return sorted(
            targets,
            key=lambda target: (target_order.get(target, len(target_order)), target),
        )

    return {
        "upstream": {
            target: order_targets(_collect_reachable_targets(target, direct_upstream))
            for target in all_targets
        },
        "downstream": {
            target: order_targets(_collect_reachable_targets(target, direct_downstream))
            for target in all_targets
        },
    }


def build_trace_targets_from_content(content: str, all_targets: List[str]) -> TraceTargets:
    """Return raw upstream/downstream trace-target lookups for all targets."""
    edge_trace_targets = _build_trace_targets_from_edges(content, all_targets)
    upstream_lookup: TraceLookup = {
        target: list(edge_trace_targets["upstream"].get(target, []))
        for target in all_targets
    }
    downstream_lookup: TraceLookup = {
        target: list(edge_trace_targets["downstream"].get(target, []))
        for target in all_targets
    }

    for target in all_targets:
        match = _find_named_target_assignment(RE_ALL_RELATED, content, target)
        if not match:
            continue

        upstream_targets = dedupe_targets(match.group(2).split())
        downstream_targets = dedupe_targets(match.group(3).split())
        if upstream_targets:
            upstream_lookup[target] = [item for item in upstream_targets if item != target]
        if downstream_targets:
            downstream_lookup[target] = [item for item in downstream_targets if item != target]

    return {"upstream": upstream_lookup, "downstream": downstream_lookup}


def get_retrace_targets(run_dir: str, target: str, inout: str) -> List[str]:
    """Return related targets from .target_dependency.csh for one direction."""
    if not run_dir or not target:
        return []

    dep_file = os.path.join(run_dir, ".target_dependency.csh")
    content = read_dependency_content(dep_file)
    if not content:
        return []

    try:
        direction_key = _direction_key(inout)
        match = _find_named_target_assignment(RE_ALL_RELATED, content, target)
        if match:
            if direction_key == "upstream":
                upstream_targets = dedupe_targets(match.group(2).split())
                if upstream_targets:
                    return upstream_targets
            else:
                downstream_targets = dedupe_targets(match.group(3).split())
                if downstream_targets:
                    return downstream_targets

        all_targets = _collect_targets_from_dependency_content(content)
        trace_targets = _build_trace_targets_from_edges(content, all_targets)
        return trace_targets[direction_key].get(target, [])
    except Exception as exc:
        logger.error(f"Error retrieving retrace targets for {target}: {exc}")
        return []


def _collect_targets_from_dependency_content(content: str) -> List[str]:
    """Collect targets in display order from dependency content."""
    targets_by_level: TargetsByLevel = {}
    for line in content.splitlines():
        line_match = re.match(r'^set\s+LEVEL_(\d+)\s*=\s*"([^"]*)"', line.strip())
        if not line_match:
            continue
        targets_by_level[int(line_match.group(1))] = line_match.group(2).split()

    ordered_targets = list_all_targets(targets_by_level)
    direct_targets = set(ordered_targets)
    for match in RE_DEPENDENCY_OUT.finditer(content):
        direct_targets.add(match.group(1))
        direct_targets.update(match.group(2).split())

    ordered_targets.extend(sorted(direct_targets.difference(ordered_targets)))
    return dedupe_targets(ordered_targets)


def _collapse_level_targets(level_targets: List[str], collapsible_groups: CollapsibleTargetGroups) -> List[List[str]]:
    groups: List[List[str]] = []
    assigned_targets = set()
    for group_targets in collapsible_groups.values():
        matching_targets = [target for target in group_targets if target in level_targets]
        if len(matching_targets) < 2:
            continue
        groups.append(matching_targets)
        assigned_targets.update(matching_targets)

    for target_name in level_targets:
        if target_name not in assigned_targets:
            groups.append([target_name])
    return groups


def _select_group_status(member_statuses: Dict[str, str]) -> str:
    for status_key in GROUP_STATUS_PRIORITY:
        if status_key and status_key in member_statuses.values():
            return status_key
    return ""


def _build_grouped_graph_nodes(
    targets_by_level: TargetsByLevel,
    collapsible_groups: CollapsibleTargetGroups,
    status_lookup: Callable[[str], str],
) -> Dict[str, object]:
    nodes: List[tuple] = []
    levels: Dict[int, List[str]] = {}
    node_meta: NodeMeta = {}
    target_to_node: Dict[str, str] = {}

    group_id_by_label = {
        label: f"{GRAPH_GROUP_PREFIX}{label}" for label in collapsible_groups.keys()
    }

    for level, level_targets in sorted(targets_by_level.items()):
        level_node_ids: List[str] = []
        for target_group in _collapse_level_targets(level_targets, collapsible_groups):
            group_label = None
            node_id = target_group[0]
            if len(target_group) > 1:
                for label, group_targets in collapsible_groups.items():
                    if target_group == [target for target in group_targets if target in level_targets]:
                        group_label = label
                        break
                if group_label:
                    node_id = group_id_by_label[group_label]

            if len(target_group) > 1 and group_label:
                member_statuses = {
                    target_name: status_lookup(target_name)
                    for target_name in target_group
                }
                status_key = _select_group_status(member_statuses)
                node_meta[node_id] = {
                    "label": group_label,
                    "kind": "group",
                    "members": list(target_group),
                    "member_statuses": member_statuses,
                    "representative_target": target_group[0],
                    "status_text": status_key,
                }
                nodes.append((node_id, status_key))
                for target_name in target_group:
                    target_to_node[target_name] = node_id
            else:
                target_name = target_group[0]
                status_key = status_lookup(target_name)
                node_meta[node_id] = {
                    "label": target_name,
                    "kind": "target",
                    "members": [target_name],
                    "member_statuses": {target_name: status_key},
                    "representative_target": target_name,
                    "status_text": status_key,
                }
                nodes.append((node_id, status_key))
                target_to_node[target_name] = node_id
            level_node_ids.append(node_id)
        if level_node_ids:
            levels[level] = level_node_ids

    return {
        "nodes": nodes,
        "levels": levels,
        "node_meta": node_meta,
        "target_to_node": target_to_node,
    }


def _group_dependency_edges(
    direct_downstream: TraceLookup,
    all_targets: List[str],
    target_to_node: Dict[str, str],
) -> List[tuple]:
    edges: List[tuple] = []
    seen_edges = set()
    for source in all_targets:
        source_node = target_to_node.get(source, source)
        for downstream in direct_downstream.get(source, []):
            target_node = target_to_node.get(downstream, downstream)
            if not source_node or not target_node or source_node == target_node:
                continue
            edge_key = (source_node, target_node)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(edge_key)
    return edges


def _group_trace_targets(
    raw_trace_targets: TraceTargets,
    node_meta: NodeMeta,
    target_to_node: Dict[str, str],
) -> TraceTargets:
    grouped_trace_targets: TraceTargets = {"upstream": {}, "downstream": {}}
    for direction_key in ("upstream", "downstream"):
        direction_lookup = raw_trace_targets.get(direction_key, {})
        for node_id, metadata in node_meta.items():
            member_targets = list(metadata.get("members", []) or [])
            related_node_ids: List[str] = []
            seen_node_ids = set()
            for member_target in member_targets:
                for related_target in direction_lookup.get(member_target, []):
                    related_node_id = target_to_node.get(related_target, related_target)
                    if (
                        not related_node_id
                        or related_node_id == node_id
                        or related_node_id in seen_node_ids
                    ):
                        continue
                    seen_node_ids.add(related_node_id)
                    related_node_ids.append(related_node_id)
            grouped_trace_targets[direction_key][node_id] = related_node_ids
    return grouped_trace_targets


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
        all_targets = list_all_targets(targets_by_level)

        effective_cache = status_cache
        if not effective_cache or effective_cache.get("run") != run_name:
            effective_cache = build_status_cache(run_base_dir, run_name)

        def status_lookup(target_name: str) -> str:
            return get_target_status(run_base_dir, run_name, target_name, effective_cache)

        collapsible_groups = parse_collapsible_target_groups(run_base_dir, run_name)
        grouped_graph = _build_grouped_graph_nodes(targets_by_level, collapsible_groups, status_lookup)
        graph_data["nodes"] = grouped_graph["nodes"]
        graph_data["levels"] = grouped_graph["levels"]
        graph_data["node_meta"] = grouped_graph["node_meta"]
        graph_data["target_to_node"] = grouped_graph["target_to_node"]

        content = read_dependency_content(dep_file)
        direct_downstream = build_direct_downstream_map(content, all_targets)
        raw_trace_targets = build_trace_targets_from_content(content, all_targets)
        graph_data["trace_targets"] = _group_trace_targets(
            raw_trace_targets,
            graph_data.get("node_meta", {}),
            graph_data.get("target_to_node", {}),
        )
        graph_data["edges"] = _group_dependency_edges(
            direct_downstream,
            all_targets,
            graph_data.get("target_to_node", {}),
        )
    except Exception as exc:
        logger.error(f"Error building dependency graph: {exc}")

    return graph_data
