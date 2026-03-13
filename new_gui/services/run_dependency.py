"""Dependency parsing and dependency-graph helpers."""

import os
import re
from typing import Dict, List, Optional

from new_gui.config.settings import (
    RE_ACTIVE_TARGETS,
    RE_DEPENDENCY_OUT,
    RE_LEVEL_LINE,
    logger,
)
from new_gui.services.run_status import build_status_cache, get_target_status


TargetsByLevel = Dict[int, List[str]]
DependencyGraph = Dict[str, object]


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


def get_retrace_targets(run_dir: str, target: str, inout: str) -> List[str]:
    """Parse .target_dependency.csh to find related targets."""
    retrace_targets: List[str] = []
    if not run_dir:
        return retrace_targets

    dep_file = os.path.join(run_dir, ".target_dependency.csh")
    if not os.path.exists(dep_file):
        return retrace_targets

    try:
        with open(dep_file, "r") as handle:
            content = handle.read()

        if inout == "in":
            pattern = re.compile(rf'set\s+ALL_RELATED_{re.escape(target)}\s*=\s*"([^"]*)"')
        else:
            pattern = re.compile(rf'set\s+DEPENDENCY_OUT_{re.escape(target)}\s*=\s*"([^"]*)"')

        match = pattern.search(content)
        if match:
            retrace_targets = match.group(1).split()
    except Exception as exc:
        logger.error(f"Error parsing dependencies: {exc}")

    return retrace_targets


def build_dependency_graph(
    run_base_dir: str,
    run_name: str,
    status_cache: Optional[Dict[str, object]] = None,
) -> DependencyGraph:
    """Build dependency graph data from .target_dependency.csh."""
    graph_data: DependencyGraph = {
        "nodes": [],
        "edges": [],
        "levels": {},
    }

    dep_file = os.path.join(run_base_dir, run_name, ".target_dependency.csh")
    if not os.path.exists(dep_file):
        logger.warning(f"Dependency file not found for {run_name}")
        return graph_data

    try:
        targets_by_level = parse_dependency_file(run_base_dir, run_name)
        graph_data["levels"] = targets_by_level

        all_targets: List[str] = []
        for targets in targets_by_level.values():
            all_targets.extend(targets)

        effective_cache = status_cache
        if not effective_cache or effective_cache.get("run") != run_name:
            effective_cache = build_status_cache(run_base_dir, run_name)

        for target in all_targets:
            status = get_target_status(run_base_dir, run_name, target, effective_cache)
            graph_data["nodes"].append((target, status))

        with open(dep_file, "r") as handle:
            content = handle.read()

        all_targets_set = set(all_targets)
        for match in RE_DEPENDENCY_OUT.finditer(content):
            source = match.group(1)
            if source not in all_targets_set:
                continue
            downstream_targets = match.group(2).strip().split()
            for downstream in downstream_targets:
                if downstream in all_targets_set:
                    graph_data["edges"].append((source, downstream))
    except Exception as exc:
        logger.error(f"Error building dependency graph: {exc}")

    return graph_data
