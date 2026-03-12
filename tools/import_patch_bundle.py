#!/usr/bin/env python3
"""Import a text-chunked patch bundle and apply it safely."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


PART_BEGIN = "-----BEGIN NEWGUI BUNDLE PART-----"
PART_END = "-----END NEWGUI BUNDLE PART-----"
DEFAULT_TARGET_ROOT = "."


def sha256_text(text: str) -> str:
    """Return sha256 for UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Return sha256 for bytes."""
    return hashlib.sha256(data).hexdigest()


def read_input_text(input_path: str | None) -> str:
    """Read chunk text from file or stdin."""
    if input_path:
        return Path(input_path).read_text(encoding="utf-8")
    return sys.stdin.read()


def parse_parts(raw_text: str) -> List[Dict[str, str]]:
    """Parse all chunk blocks."""
    blocks = [block.strip() for block in raw_text.split(PART_BEGIN) if block.strip()]
    if not blocks:
        raise SystemExit("No bundle parts found in input.")

    parsed_parts: List[Dict[str, str]] = []
    for block in blocks:
        if PART_END not in block:
            raise SystemExit("Malformed chunk block: missing end marker.")

        body = block.split(PART_END, 1)[0].strip("\n")
        if "\npayload:\n" not in body:
            raise SystemExit("Malformed chunk block: missing payload section.")

        header_text, payload = body.split("\npayload:\n", 1)
        headers: Dict[str, str] = {}
        for line in header_text.splitlines():
            if ":" not in line:
                raise SystemExit(f"Malformed header line: {line}")
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

        payload = payload.strip()
        if sha256_text(payload) != headers.get("part_sha256", ""):
            raise SystemExit(f"Part hash mismatch for bundle part {headers.get('part', '?')}.")

        headers["payload"] = payload
        parsed_parts.append(headers)

    return parsed_parts


def rebuild_bundle(parts: List[Dict[str, str]]) -> Dict[str, str]:
    """Validate and reconstruct bundle payload."""
    bundle_ids = {part.get("bundle_id") for part in parts}
    if len(bundle_ids) != 1:
        raise SystemExit("Bundle contains mixed bundle_id values.")

    compressed_hashes = {part.get("compressed_sha256") for part in parts}
    if len(compressed_hashes) != 1:
        raise SystemExit("Bundle contains mixed compressed_sha256 values.")

    expected_total = None
    ordered_parts: Dict[int, str] = {}
    for part in parts:
        match = re.fullmatch(r"(\d+)/(\d+)", part.get("part", ""))
        if not match:
            raise SystemExit(f"Invalid part header: {part.get('part', '')}")
        index = int(match.group(1))
        total = int(match.group(2))
        if expected_total is None:
            expected_total = total
        elif expected_total != total:
            raise SystemExit("Bundle contains inconsistent total part counts.")
        if index in ordered_parts:
            raise SystemExit(f"Duplicate part index detected: {index}")
        ordered_parts[index] = part["payload"]

    if expected_total is None:
        raise SystemExit("Bundle contains no part metadata.")
    if set(ordered_parts.keys()) != set(range(1, expected_total + 1)):
        raise SystemExit("Bundle is missing one or more parts.")

    encoded_payload = "".join(ordered_parts[index] for index in range(1, expected_total + 1))
    compressed = base64.b64decode(encoded_payload.encode("ascii"), validate=True)
    expected_compressed_hash = compressed_hashes.pop()
    if sha256_bytes(compressed) != expected_compressed_hash:
        raise SystemExit("Compressed payload hash mismatch.")

    try:
        bundle = json.loads(gzip.decompress(compressed).decode("utf-8"))
    except (gzip.BadGzipFile, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SystemExit(f"Failed to decode bundle: {exc}")

    return bundle


def parse_unified_diff(diff_text: str) -> List[Dict[str, object]]:
    """Parse unified diff hunks."""
    hunk_header = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    lines = diff_text.splitlines(keepends=True)
    hunks: List[Dict[str, object]] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if line.startswith("--- ") or line.startswith("+++ "):
            index += 1
            continue

        match = hunk_header.match(line)
        if not match:
            index += 1
            continue

        old_start = int(match.group(1))
        old_count = int(match.group(2) or "1")
        new_start = int(match.group(3))
        new_count = int(match.group(4) or "1")
        index += 1

        hunk_lines: List[str] = []
        while index < len(lines):
            current = lines[index]
            if current.startswith("@@"):
                break
            if current.startswith("\\ No newline at end of file"):
                index += 1
                continue
            hunk_lines.append(current)
            index += 1

        hunks.append(
            {
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "lines": hunk_lines,
            }
        )

    if not hunks:
        raise SystemExit("Bundle diff does not contain any hunks.")
    return hunks


def apply_unified_diff(base_text: str, diff_text: str) -> str:
    """Apply a unified diff to text and return the new text."""
    base_lines = base_text.splitlines(keepends=True)
    hunks = parse_unified_diff(diff_text)
    output: List[str] = []
    cursor = 0

    for hunk in hunks:
        old_start = int(hunk["old_start"]) - 1
        if old_start < cursor:
            raise SystemExit("Invalid diff: overlapping hunk positions.")

        output.extend(base_lines[cursor:old_start])
        cursor = old_start

        for diff_line in hunk["lines"]:
            if not diff_line:
                continue
            prefix = diff_line[0]
            content = diff_line[1:]

            if prefix == " ":
                if cursor >= len(base_lines) or base_lines[cursor] != content:
                    raise SystemExit("Patch context mismatch while applying unified diff.")
                output.append(content)
                cursor += 1
            elif prefix == "-":
                if cursor >= len(base_lines) or base_lines[cursor] != content:
                    raise SystemExit("Patch delete mismatch while applying unified diff.")
                cursor += 1
            elif prefix == "+":
                output.append(content)
            else:
                raise SystemExit(f"Unsupported diff line prefix: {prefix}")

    output.extend(base_lines[cursor:])
    return "".join(output)


def backup_file(target_path: Path) -> Path:
    """Create a timestamped backup file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target_path.with_name(f"{target_path.name}.{timestamp}.bak")
    shutil.copy2(target_path, backup_path)
    return backup_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="File containing all pasted bundle parts. Reads stdin when omitted.")
    parser.add_argument("--root", default=DEFAULT_TARGET_ROOT, help="Project root for relative target paths")
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    raw_text = read_input_text(args.input)
    parts = parse_parts(raw_text)
    bundle = rebuild_bundle(parts)

    required_keys = {"bundle_id", "mode", "target_path", "target_hash", "payload"}
    missing = required_keys - set(bundle.keys())
    if missing:
        raise SystemExit(f"Bundle metadata is missing required keys: {', '.join(sorted(missing))}")

    repo_root = Path(args.root).resolve()
    if repo_root.exists() and not repo_root.is_dir():
        raise SystemExit(f"--root must be a project directory, not a file: {repo_root}")
    target_path = (repo_root / bundle["target_path"]).resolve()
    if repo_root not in target_path.parents and target_path != repo_root:
        raise SystemExit(f"Target path escapes the requested root: {target_path}")

    mode = bundle["mode"]
    if mode not in {"patch", "full"}:
        raise SystemExit(f"Unsupported bundle mode: {mode}")

    current_text = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
    current_hash = sha256_text(current_text) if target_path.exists() else ""
    target_hash = bundle["target_hash"]

    if current_hash == target_hash:
        print(f"Bundle {bundle['bundle_id']} is already applied for {target_path}.")
        return 0

    if mode == "patch":
        if not target_path.exists():
            raise SystemExit(f"Patch mode requires an existing target file: {target_path}")
        base_hash = bundle.get("base_hash", "")
        if current_hash != base_hash:
            raise SystemExit(
                "Baseline drift detected. "
                f"Current hash={current_hash or '<missing>'}, expected base hash={base_hash}."
            )
        new_text = apply_unified_diff(current_text, bundle["payload"])
    else:
        new_text = bundle["payload"]

    new_hash = sha256_text(new_text)
    if new_hash != target_hash:
        raise SystemExit(
            "Applied content hash mismatch. "
            f"Expected {target_hash}, got {new_hash}."
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if target_path.exists():
        backup_path = backup_file(target_path)
    target_path.write_text(new_text, encoding="utf-8")

    print(f"Applied bundle {bundle['bundle_id']} to {target_path}")
    if backup_path is not None:
        print(f"Backup created at {backup_path}")
    print(f"Result hash: {new_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
