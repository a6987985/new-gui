#!/usr/bin/env python3
"""Summarize slack distribution from data transition reports.

The script parses report lines like:
    # Net: <name>  Slack: -5.446289  Trans: 5.514389  Limit: 0.068100

It supports both plain text reports and gzip-compressed reports (.gz),
accepts multiple files/patterns, and prints per-file and merged histograms.
When multiple reports are merged, duplicated nets are removed and only the
worst slack (most negative value) for each net is kept.
"""

from __future__ import annotations

import argparse
import gzip
import math
import re
import sys
from collections import OrderedDict
from pathlib import Path
import glob
from typing import Dict, List, Sequence, Tuple


NET_SLACK_RE = re.compile(
    r"^\s*#\s*Net:\s+(.+?)\s+Slack:\s*([-+]?\d+(?:\.\d+)?)\b"
)
Entry = Tuple[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze slack distribution from data transition reports "
            "(.rpt or .rpt.gz)."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input report files or shell-style patterns.",
    )
    parser.add_argument(
        "--bin-width",
        type=float,
        default=0.5,
        help="Histogram bin width. Default: 0.5",
    )
    parser.add_argument(
        "--min",
        dest="min_value",
        type=float,
        default=None,
        help="Optional histogram lower bound. Default: auto",
    )
    parser.add_argument(
        "--max",
        dest="max_value",
        type=float,
        default=None,
        help="Optional histogram upper bound. Default: auto",
    )
    parser.add_argument(
        "--merged-only",
        action="store_true",
        help="Only print the merged histogram across all input files.",
    )
    parser.add_argument(
        "--bar-width",
        type=int,
        default=32,
        help="ASCII bar width. Default: 32",
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
    values: List[Entry] = []
    with open_text(path) as handle:
        for line in handle:
            match = NET_SLACK_RE.search(line)
            if match:
                values.append((match.group(1).strip(), float(match.group(2))))
    return values


def extract_slacks(entries: Sequence[Entry]) -> List[float]:
    return [slack for _, slack in entries]


def dedup_entries_keep_worst(entries: Sequence[Entry]) -> List[Entry]:
    deduped: Dict[str, float] = OrderedDict()
    for net_name, slack in entries:
        if net_name not in deduped or slack < deduped[net_name]:
            deduped[net_name] = slack
    return list(deduped.items())


def aligned_floor(value: float, step: float) -> float:
    return math.floor(value / step) * step


def aligned_ceil(value: float, step: float) -> float:
    return math.ceil(value / step) * step


def build_edges(
    values: Sequence[float],
    bin_width: float,
    min_value: float | None,
    max_value: float | None,
) -> List[float]:
    if not values:
        raise ValueError("No slack values found in the input reports.")

    low = min_value if min_value is not None else aligned_floor(min(values), bin_width)
    high = max_value if max_value is not None else aligned_ceil(max(values), bin_width)

    if high <= low:
        high = low + bin_width

    span = high - low
    bins = max(1, int(math.ceil(span / bin_width)))
    edges = [low + i * bin_width for i in range(bins + 1)]

    if edges[-1] < high:
        edges.append(edges[-1] + bin_width)

    return edges


def histogram(values: Sequence[float], edges: Sequence[float]) -> List[int]:
    counts = [0] * (len(edges) - 1)
    last_index = len(counts) - 1

    for value in values:
        if value < edges[0] or value > edges[-1]:
            continue
        index = int((value - edges[0]) / (edges[1] - edges[0]))
        if index > last_index:
            index = last_index
        counts[index] += 1

    return counts


def format_range(start: float, end: float, is_last: bool) -> str:
    right_bracket = "]" if is_last else ")"
    return f"[{start:8.3f}, {end:8.3f}{right_bracket}"


def print_summary(
    title: str,
    values: Sequence[float],
    edges: Sequence[float],
    bar_width: int,
) -> None:
    counts = histogram(values, edges)
    total = len(values)
    maximum = max(counts) if counts else 0

    print(f"\n=== {title} ===")
    print(f"Entries : {total}")
    print(f"Min/Max : {min(values):.6f} / {max(values):.6f}")
    print(f"Bin size: {edges[1] - edges[0]:.3f}")
    print()
    print("Range                  Count     Percent   Histogram")
    print("-" * 70)

    for idx, count in enumerate(counts):
        start = edges[idx]
        end = edges[idx + 1]
        percent = (count / total * 100.0) if total else 0.0
        filled = 0 if maximum == 0 else int(round(count / maximum * bar_width))
        bar = "#" * filled
        print(
            f"{format_range(start, end, idx == len(counts) - 1):<22} "
            f"{count:>7}  {percent:>8.2f}%   {bar}"
        )


def main() -> int:
    args = parse_args()

    if args.bin_width <= 0:
        print("Error: --bin-width must be positive.", file=sys.stderr)
        return 2

    try:
        paths = expand_inputs(args.inputs)
    except FileNotFoundError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    per_file: List[Tuple[Path, List[Entry]]] = []
    merged_entries: List[Entry] = []

    for path in paths:
        entries = extract_entries(path)
        per_file.append((path, entries))
        merged_entries.extend(entries)

    if not merged_entries:
        print("Error: no slack values were found in the input reports.", file=sys.stderr)
        return 1

    deduped_merged_entries = dedup_entries_keep_worst(merged_entries)
    deduped_merged_slacks = extract_slacks(deduped_merged_entries)
    edges = build_edges(
        deduped_merged_slacks,
        args.bin_width,
        args.min_value,
        args.max_value,
    )

    if not args.merged_only:
        for path, entries in per_file:
            if not entries:
                print(f"\n=== {path} ===")
                print("No slack values found.")
                continue
            print_summary(str(path), extract_slacks(entries), edges, args.bar_width)

    if len(per_file) > 1:
        duplicate_count = len(merged_entries) - len(deduped_merged_entries)
        print(
            f"\nMerged {len(merged_entries)} entries from {len(per_file)} files; "
            f"removed {duplicate_count} duplicate net entries by keeping the "
            "worst slack per net."
        )
        print_summary("Merged Summary (dedup by Net, keep worst slack)", deduped_merged_slacks, edges, args.bar_width)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
