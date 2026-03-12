#!/usr/bin/env python3
"""Export a text-chunked patch bundle for cross-network transfer."""

from __future__ import annotations

import argparse
import base64
import difflib
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from uuid import uuid4


STATE_DIR_NAME = ".patch_bundle_state"
STATE_FILE_NAME = "export_state.json"
BASELINE_FILE_NAME = "reproduce_ui.baseline.py"
DEFAULT_TARGET = "reproduce_ui.py"
DEFAULT_CHUNK_SIZE = 4000
PART_BEGIN = "-----BEGIN NEWGUI BUNDLE PART-----"
PART_END = "-----END NEWGUI BUNDLE PART-----"


def sha256_text(text: str) -> str:
    """Return sha256 for UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Return sha256 for bytes."""
    return hashlib.sha256(data).hexdigest()


def read_text_file(path: Path) -> str:
    """Read file as UTF-8 text."""
    return path.read_text(encoding="utf-8")


def write_text_file(path: Path, content: str) -> None:
    """Write file as UTF-8 text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_state(state_file: Path) -> Dict[str, str]:
    """Load local export state if it exists."""
    if not state_file.exists():
        return {}
    try:
        return json.loads(read_text_file(state_file))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse export state: {state_file} ({exc})")


def save_state(state_file: Path, state: Dict[str, str]) -> None:
    """Persist local export state."""
    write_text_file(state_file, json.dumps(state, indent=2, sort_keys=True) + "\n")


def build_unified_diff(target_relpath: str, baseline_text: str, current_text: str) -> str:
    """Generate unified diff text."""
    diff_lines = difflib.unified_diff(
        baseline_text.splitlines(keepends=True),
        current_text.splitlines(keepends=True),
        fromfile=f"a/{target_relpath}",
        tofile=f"b/{target_relpath}",
        lineterm="\n",
    )
    return "".join(diff_lines)


def build_bundle(
    target_relpath: str,
    baseline_text: str | None,
    current_text: str,
    force_full: bool,
) -> Dict[str, str]:
    """Build bundle metadata and payload."""
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bundle_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    target_hash = sha256_text(current_text)

    if force_full or baseline_text is None:
        return {
            "bundle_version": 1,
            "bundle_id": bundle_id,
            "created_at": created_at,
            "mode": "full",
            "target_path": target_relpath,
            "base_hash": "",
            "target_hash": target_hash,
            "payload": current_text,
        }

    diff_text = build_unified_diff(target_relpath, baseline_text, current_text)
    if not diff_text:
        raise SystemExit("No changes detected against the last exported baseline.")

    return {
        "bundle_version": 1,
        "bundle_id": bundle_id,
        "created_at": created_at,
        "mode": "patch",
        "target_path": target_relpath,
        "base_hash": sha256_text(baseline_text),
        "target_hash": target_hash,
        "payload": diff_text,
    }


def encode_bundle(bundle: Dict[str, str]) -> Dict[str, str]:
    """Serialize, compress, and encode bundle."""
    bundle_json = json.dumps(bundle, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    compressed = gzip.compress(bundle_json.encode("utf-8"))
    encoded = base64.b64encode(compressed).decode("ascii")
    return {
        "bundle_json": bundle_json,
        "compressed_sha256": sha256_bytes(compressed),
        "encoded_payload": encoded,
    }


def chunk_payload(bundle: Dict[str, str], encoded_payload: str, compressed_sha256: str, chunk_size: int) -> str:
    """Render chunked text blocks for manual transfer."""
    parts = [encoded_payload[i:i + chunk_size] for i in range(0, len(encoded_payload), chunk_size)]
    rendered_parts: List[str] = []

    for index, payload_part in enumerate(parts, start=1):
        part_sha256 = sha256_text(payload_part)
        rendered_parts.append(
            "\n".join(
                [
                    PART_BEGIN,
                    f"bundle_id: {bundle['bundle_id']}",
                    f"mode: {bundle['mode']}",
                    f"target_path: {bundle['target_path']}",
                    f"part: {index}/{len(parts)}",
                    f"compressed_sha256: {compressed_sha256}",
                    f"part_sha256: {part_sha256}",
                    "payload:",
                    payload_part,
                    PART_END,
                ]
            )
        )

    return "\n\n".join(rendered_parts) + "\n"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Target file to export")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Chunk size in characters")
    parser.add_argument("--full", action="store_true", help="Force a full bundle instead of a patch bundle")
    parser.add_argument("--output", help="Write chunked bundle text to a file instead of stdout")
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    target_path = (repo_root / args.target).resolve()
    target_relpath = target_path.relative_to(repo_root).as_posix()

    if not target_path.exists():
        raise SystemExit(f"Target file not found: {target_path}")
    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size must be a positive integer")

    state_dir = repo_root / "tools" / STATE_DIR_NAME
    state_file = state_dir / STATE_FILE_NAME
    baseline_file = state_dir / BASELINE_FILE_NAME

    state = load_state(state_file)
    current_text = read_text_file(target_path)
    baseline_text = read_text_file(baseline_file) if baseline_file.exists() else None

    bundle = build_bundle(target_relpath, baseline_text, current_text, args.full)
    encoded = encode_bundle(bundle)
    chunk_text = chunk_payload(bundle, encoded["encoded_payload"], encoded["compressed_sha256"], args.chunk_size)

    output_path = Path(args.output).resolve() if args.output else None
    if output_path is not None:
        write_text_file(output_path, chunk_text)
        print(f"Wrote chunked bundle to {output_path}")
    else:
        sys.stdout.write(chunk_text)

    write_text_file(baseline_file, current_text)
    state.update(
        {
            "bundle_version": 1,
            "last_bundle_id": bundle["bundle_id"],
            "last_exported_at": bundle["created_at"],
            "last_mode": bundle["mode"],
            "last_target_path": target_relpath,
            "last_target_hash": bundle["target_hash"],
            "last_base_hash": bundle["base_hash"],
        }
    )
    save_state(state_file, state)

    summary = (
        f"bundle_id={bundle['bundle_id']} mode={bundle['mode']} "
        f"target={bundle['target_path']} target_hash={bundle['target_hash']} "
        f"compressed_sha256={encoded['compressed_sha256']}"
    )
    print(summary, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
