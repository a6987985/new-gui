"""Dependency-file parsing helpers."""

from __future__ import annotations

import os
import re
from typing import Dict, List

from new_gui.shared.config.settings import RE_ACTIVE_TARGETS, RE_LEVEL_LINE, logger


TargetsByLevel = Dict[int, List[str]]
CollapsibleTargetGroups = Dict[str, List[str]]
GRAPH_GROUP_PREFIX = "__group__"

RE_INSTANCES_LIST_LINE = re.compile(
    r'^\s*set\s+INSTANCES_LIST_([A-Za-z0-9_]+)\s*=\s*"([^"]*)"',
    re.MULTILINE,
)
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


def read_dependency_content(dependency_file: str) -> str:
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


def list_all_targets(targets_by_level: TargetsByLevel) -> List[str]:
    """Flatten level groups into a stable target list."""
    all_targets: List[str] = []
    for level in sorted(targets_by_level.keys()):
        all_targets.extend(targets_by_level.get(level) or [])
    return all_targets


def dedupe_targets(targets: List[str]) -> List[str]:
    """Return targets with duplicates removed while preserving order."""
    seen = set()
    ordered_targets: List[str] = []
    for target in targets:
        if not target or target in seen:
            continue
        seen.add(target)
        ordered_targets.append(target)
    return ordered_targets


def normalize_collapsible_group_label(raw_group_name: str) -> str:
    """Return the display label used for a collapsible target group."""
    normalized_group_name = raw_group_name or ""
    for prefix in ("TIMING_", "SORTTIMING_"):
        if normalized_group_name.startswith(prefix):
            normalized_group_name = normalized_group_name[len(prefix):]
            break
    return normalized_group_name.replace("_", "")


def parse_collapsible_target_groups(run_base_dir: str, run_name: str) -> CollapsibleTargetGroups:
    """Parse large generic-instance groups from the dependency file."""
    dependency_file = os.path.join(run_base_dir, run_name, ".target_dependency.csh")
    content = read_dependency_content(dependency_file)
    if not content:
        return {}

    grouped_targets: CollapsibleTargetGroups = {}
    for match in RE_INSTANCES_LIST_LINE.finditer(content):
        raw_group_name = match.group(1)
        instances = [item for item in match.group(2).split() if item]
        if len(instances) < MIN_COLLAPSIBLE_GROUP_SIZE:
            continue
        if COLLAPSIBLE_GROUP_MARKER not in raw_group_name:
            continue
        display_label = normalize_collapsible_group_label(raw_group_name)
        if not display_label:
            continue
        grouped_targets[display_label] = instances
    return grouped_targets
