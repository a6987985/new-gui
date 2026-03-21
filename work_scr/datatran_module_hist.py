#!/usr/bin/env python3
"""Summarize net distribution by module hierarchy from data transition reports.

The script is fully standalone:
1. Read one or more .rpt / .rpt.gz files
2. Merge all nets across files
3. Deduplicate by Net and keep the worst slack (most negative)
4. Count net distribution by module hierarchy prefixes

Example:
    tile_dfx/net6760225
      -> level1: tile_dfx

    u_vcpu/u_cpu/u_iside/u_fetch/u_ibiu/u_itag_plru/preCTS...
      -> level1: u_vcpu
      -> level2: u_vcpu/u_cpu
      -> level3: u_vcpu/u_cpu/u_iside
      -> level4: u_vcpu/u_cpu/u_iside/u_fetch
"""

from __future__ import annotations

import argparse
import csv
import glob
import gzip
import re
import sys
from collections import defaultdict
from collections import OrderedDict
from pathlib import Path
from typing import DefaultDict, Dict, List, Sequence, Tuple


Entry = Tuple[str, float]
Stats = Dict[str, float]
NET_SLACK_RE = re.compile(
    r"^\s*#\s*Net:\s+(.+?)\s+Slack:\s*([-+]?\d+(?:\.\d+)?)\b"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze net distribution by module hierarchy from data transition "
            "reports (.rpt or .rpt.gz)."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input report files or shell-style patterns.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=4,
        help="Maximum hierarchy depth to summarize. Default: 4",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=50,
        help="Show top N modules per hierarchy depth. Default: 50",
    )
    parser.add_argument(
        "--csv-out",
        type=Path,
        default=None,
        help="Optional CSV output path.",
    )
    return parser.parse_args()


def expand_inputs(items: Sequence[str]) -> List[Path]:
    paths: "OrderedDict[str, Path]" = OrderedDict()
    for item in items:
        matched = sorted(glob.glob(item))
        if matched:
            for match in matched:
                path = Path(match)
                if path.is_file():
                    paths[str(path.resolve())] = path.resolve()
            continue

        path = Path(item).expanduser()
        if path.is_file():
            paths[str(path.resolve())] = path.resolve()
            continue

        raise FileNotFoundError(f"Input not found: {item}")

    if not paths:
        raise FileNotFoundError("No valid input reports were found.")

    return list(paths.values())


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("rt", encoding="utf-8", errors="ignore")


def extract_entries(path: Path) -> List[Entry]:
    entries: List[Entry] = []
    with open_text(path) as handle:
        for line in handle:
            match = NET_SLACK_RE.search(line)
            if match:
                entries.append((match.group(1).strip(), float(match.group(2))))
    return entries


def dedup_entries_keep_worst(entries: Sequence[Entry]) -> List[Entry]:
    deduped: Dict[str, float] = OrderedDict()
    for net_name, slack in entries:
        if net_name not in deduped or slack < deduped[net_name]:
            deduped[net_name] = slack
    return list(deduped.items())


def module_prefixes(net_name: str, max_depth: int) -> List[str]:
    parts = [part for part in net_name.strip().split("/") if part]
    if not parts:
        return ["<top>"]

    module_parts = parts[:-1]
    if not module_parts:
        return ["<top>"]

    limit = min(max_depth, len(module_parts))
    return ["/".join(module_parts[:depth]) for depth in range(1, limit + 1)]


def build_level_tables(
    entries: Sequence[Entry],
    max_depth: int,
) -> Dict[int, Dict[str, List[float]]]:
    level_tables: DefaultDict[int, DefaultDict[str, List[float]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for net_name, slack in entries:
        for level, prefix in enumerate(module_prefixes(net_name, max_depth), start=1):
            level_tables[level][prefix].append(slack)

    return {level: dict(table) for level, table in level_tables.items()}


def summarize_level(level_table: Dict[str, List[float]]) -> List[Tuple[str, Stats]]:
    rows: List[Tuple[str, Stats]] = []
    for module_name, slacks in level_table.items():
        count = len(slacks)
        worst_slack = min(slacks)
        avg_slack = sum(slacks) / count
        rows.append(
            (
                module_name,
                {
                    "count": count,
                    "worst_slack": worst_slack,
                    "avg_slack": avg_slack,
                },
            )
        )

    rows.sort(
        key=lambda item: (
            -int(item[1]["count"]),
            float(item[1]["worst_slack"]),
            item[0],
        )
    )
    return rows


def print_level_summary(
    level: int,
    rows: Sequence[Tuple[str, Stats]],
    total_nets: int,
    top_n: int,
) -> None:
    visible_rows = rows[:top_n]
    print(f"\n=== Module Level {level} ===")
    print(f"Unique modules: {len(rows)}")
    print()
    print("Module Path                               Nets    Percent   WorstSlack   AvgSlack")
    print("-" * 86)

    for module_name, stats in visible_rows:
        count = int(stats["count"])
        percent = (count / total_nets * 100.0) if total_nets else 0.0
        print(
            f"{module_name:<40} {count:>6}  {percent:>8.2f}%  "
            f"{stats['worst_slack']:>11.6f}  {stats['avg_slack']:>10.6f}"
        )

    if len(rows) > top_n:
        print(f"... ({len(rows) - top_n} more modules omitted)")


def write_csv(
    path: Path,
    summaries: Dict[int, List[Tuple[str, Stats]]],
    total_nets: int,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "level",
                "module_path",
                "net_count",
                "percent",
                "worst_slack",
                "avg_slack",
            ]
        )

        for level in sorted(summaries):
            for module_name, stats in summaries[level]:
                count = int(stats["count"])
                percent = (count / total_nets * 100.0) if total_nets else 0.0
                writer.writerow(
                    [
                        level,
                        module_name,
                        count,
                        f"{percent:.6f}",
                        f"{stats['worst_slack']:.6f}",
                        f"{stats['avg_slack']:.6f}",
                    ]
                )


def main() -> int:
    args = parse_args()

    if args.max_depth <= 0:
        raise SystemExit("Error: --max-depth must be positive.")
    if args.top <= 0:
        raise SystemExit("Error: --top must be positive.")

    try:
        paths = expand_inputs(args.inputs)
    except FileNotFoundError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    merged_entries: List[Entry] = []
    for path in paths:
        merged_entries.extend(extract_entries(path))

    if not merged_entries:
        raise SystemExit("Error: no net/slack entries were found in the input reports.")

    deduped_entries = dedup_entries_keep_worst(merged_entries)
    duplicate_count = len(merged_entries) - len(deduped_entries)
    total_unique_nets = len(deduped_entries)

    print(
        f"Merged {len(merged_entries)} entries from {len(paths)} files; "
        f"removed {duplicate_count} duplicate net entries by keeping the "
        "worst slack per net."
    )
    print(f"Total unique nets after dedup: {total_unique_nets}")

    level_tables = build_level_tables(deduped_entries, args.max_depth)
    summaries: Dict[int, List[Tuple[str, Stats]]] = {}

    for level in sorted(level_tables):
        summaries[level] = summarize_level(level_tables[level])
        print_level_summary(level, summaries[level], total_unique_nets, args.top)

    if args.csv_out is not None:
        write_csv(args.csv_out, summaries, total_unique_nets)
        print(f"\nCSV written to: {args.csv_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
