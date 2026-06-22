#!/usr/bin/env python3
"""Generate a unified multi-year GitHub contribution heatmap (SVG)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

GRAPHQL_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        colors
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

LEVEL_TO_INDEX = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


@dataclass
class Theme:
    background: str
    text: str
    border: str
    muted: str


THEMES = {
    "light": Theme(
        background="#ffffff",
        text="#1f2328",
        border="#d0d7de",
        muted="#656d76",
    ),
    "dark": Theme(
        background="#0d1117",
        text="#e6edf3",
        border="#30363d",
        muted="#8b949e",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a unified GitHub contribution heatmap (SVG) for a custom date range.",
    )
    parser.add_argument("--username", required=True, help="GitHub username")
    parser.add_argument(
        "--start",
        default="2024-01-01",
        help="Start date in YYYY-MM-DD (default: 2024-01-01)",
    )
    parser.add_argument(
        "--end",
        default="2026-12-31",
        help="End date in YYYY-MM-DD (default: 2026-12-31)",
    )
    parser.add_argument(
        "--theme",
        choices=sorted(THEMES.keys()),
        default="dark",
        help="Chart theme (default: dark)",
    )
    parser.add_argument(
        "--output",
        default="github_heatmap_2024_2026.svg",
        help="Output SVG file path",
    )
    return parser.parse_args()


def iso_datetime_utc(date_str: str, end_of_day: bool = False) -> str:
    date_obj = dt.date.fromisoformat(date_str)
    if end_of_day:
        value = dt.datetime.combine(date_obj, dt.time(23, 59, 59), tzinfo=dt.timezone.utc)
    else:
        value = dt.datetime.combine(date_obj, dt.time(0, 0, 0), tzinfo=dt.timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def load_token() -> str:
    token = (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_PAT")
        or ""
    ).strip()
    if not token:
        raise RuntimeError(
            "Missing GitHub token. Set GITHUB_TOKEN (or GH_TOKEN / GITHUB_PAT) and retry."
        )
    return token


def fetch_calendar(username: str, from_iso: str, to_iso: str, token: str) -> dict:
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {
            "login": username,
            "from": from_iso,
            "to": to_iso,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-three-year-heatmap-script",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_data = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API network error: {exc}") from exc

    parsed = json.loads(response_data)
    if parsed.get("errors"):
        raise RuntimeError(f"GitHub API returned errors: {parsed['errors']}")
    user_data = (((parsed.get("data") or {}).get("user") or {}))
    if not user_data:
        raise RuntimeError(f"GitHub user not found or token has no access: {username}")
    calendar = (
        (user_data.get("contributionsCollection") or {})
        .get("contributionCalendar")
        or {}
    )
    if not calendar:
        raise RuntimeError("GitHub contribution calendar is empty in API response.")
    return calendar


def month_start_indices(weeks: list[dict]) -> list[tuple[int, str]]:
    labels: list[tuple[int, str]] = []
    seen = set()
    for week_idx, week in enumerate(weeks):
        days = week.get("contributionDays") or []
        for day in days:
            date_str = str(day.get("date") or "")
            if not date_str:
                continue
            day_obj = dt.date.fromisoformat(date_str)
            if day_obj.day == 1:
                key = (day_obj.year, day_obj.month)
                if key in seen:
                    continue
                seen.add(key)
                labels.append((week_idx, day_obj.strftime("%b")))
    return labels


def render_svg(username: str, start: str, end: str, calendar: dict, theme: Theme) -> str:
    weeks = calendar.get("weeks") or []
    total = int(calendar.get("totalContributions") or 0)
    palette = list(calendar.get("colors") or [])
    if len(palette) < 5:
        palette = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

    cell = 12
    gap = 4
    left = 90
    top = 88
    title_h = 36
    month_h = 26
    right_pad = 24
    bottom_pad = 70
    grid_w = len(weeks) * (cell + gap)
    grid_h = 7 * (cell + gap)

    width = left + grid_w + right_pad
    height = top + grid_h + bottom_pad

    month_labels = month_start_indices(weeks)
    week_day_labels = [
        (1, "Mon"),
        (3, "Wed"),
        (5, "Fri"),
    ]

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
    lines.append(f'<rect width="{width}" height="{height}" fill="{theme.background}"/>')
    lines.append(
        f'<text x="{left}" y="{title_h}" fill="{theme.text}" font-size="18" font-family="Inter, Segoe UI, sans-serif">'
        f'{username}: {total} contributions ({start} to {end})'
        "</text>"
    )
    lines.append(
        f'<rect x="{left - 12}" y="{top - 38}" width="{grid_w + 24}" height="{grid_h + 56}" '
        f'rx="10" ry="10" fill="none" stroke="{theme.border}" stroke-width="1"/>'
    )

    for idx, label in month_labels:
        x = left + idx * (cell + gap)
        lines.append(
            f'<text x="{x}" y="{top - 12}" fill="{theme.text}" font-size="14" font-family="Inter, Segoe UI, sans-serif">{label}</text>'
        )

    for day_idx, label in week_day_labels:
        y = top + day_idx * (cell + gap) + cell - 1
        lines.append(
            f'<text x="{left - 58}" y="{y}" fill="{theme.text}" font-size="13" font-family="Inter, Segoe UI, sans-serif">{label}</text>'
        )

    for week_idx, week in enumerate(weeks):
        days = week.get("contributionDays") or []
        for day_idx, day in enumerate(days):
            level = str(day.get("contributionLevel") or "NONE").upper()
            color_idx = LEVEL_TO_INDEX.get(level, 0)
            color = palette[color_idx] if color_idx < len(palette) else palette[0]
            x = left + week_idx * (cell + gap)
            y = top + day_idx * (cell + gap)
            count = int(day.get("contributionCount") or 0)
            date_str = str(day.get("date") or "")
            lines.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" ry="3" fill="{color}">'
                f'<title>{date_str}: {count} contributions</title>'
                "</rect>"
            )

    legend_x = left + grid_w - 230
    legend_y = top + grid_h + 22
    lines.append(
        f'<text x="{legend_x}" y="{legend_y}" fill="{theme.muted}" font-size="13" font-family="Inter, Segoe UI, sans-serif">Less</text>'
    )
    for idx in range(5):
        box_x = legend_x + 40 + idx * (cell + 6)
        lines.append(
            f'<rect x="{box_x}" y="{legend_y - 11}" width="{cell}" height="{cell}" rx="3" ry="3" fill="{palette[idx]}"/>'
        )
    lines.append(
        f'<text x="{legend_x + 40 + 5 * (cell + 6) + 4}" y="{legend_y}" fill="{theme.muted}" font-size="13" font-family="Inter, Segoe UI, sans-serif">More</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        start_date = dt.date.fromisoformat(args.start)
        end_date = dt.date.fromisoformat(args.end)
    except ValueError as exc:
        print(f"Invalid date format: {exc}", file=sys.stderr)
        return 2

    if start_date > end_date:
        print("Start date must be earlier than or equal to end date.", file=sys.stderr)
        return 2

    try:
        token = load_token()
        calendar = fetch_calendar(
            args.username.strip(),
            iso_datetime_utc(args.start, end_of_day=False),
            iso_datetime_utc(args.end, end_of_day=True),
            token,
        )
        theme = THEMES[args.theme]
        svg = render_svg(args.username.strip(), args.start, args.end, calendar, theme)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(svg)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Failed: {exc}", file=sys.stderr)
        return 1

    print(f"Done. Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

