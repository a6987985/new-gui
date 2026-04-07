#!/usr/bin/env python3
"""Export a text-chunked patch bundle for cross-network transfer."""

from __future__ import annotations

import argparse
import base64
import difflib
import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from uuid import uuid4


STATE_DIR_NAME = ".patch_bundle_state"
STATE_FILE_NAME = "export_state.json"
SNAPSHOT_ROOT_NAME = "baseline_snapshots"
DEFAULT_TARGET = "new_gui"
DEFAULT_CHUNK_SIZE = 4000
PART_BEGIN = "-----BEGIN NEWGUI BUNDLE PART-----"
PART_END = "-----END NEWGUI BUNDLE PART-----"
IGNORED_DIR_NAMES = {"__pycache__"}
IGNORED_FILE_NAMES = {".DS_Store"}
IGNORED_SUFFIXES = {".pyc"}


TextMap = Dict[str, str]


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


def target_slug(target_relpath: str) -> str:
    """Return a filesystem-safe token for a target path."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", target_relpath.strip("/"))
    return slug or "root"


def should_include_file(path: Path) -> bool:
    """Return True when a file should be included in the bundle scope."""
    if any(part in IGNORED_DIR_NAMES for part in path.parts):
        return False
    if path.name in IGNORED_FILE_NAMES:
        return False
    if path.suffix in IGNORED_SUFFIXES:
        return False
    return True


def collect_scope_texts(
    scope_path: Path,
    repo_root: Path,
    excluded_relpaths: set[str] | None = None,
) -> TextMap:
    """Collect all text files under a target file or directory."""
    if not scope_path.exists():
        raise SystemExit(f"Target path not found: {scope_path}")

    excluded_relpaths = excluded_relpaths or set()
    collected: TextMap = {}
    if scope_path.is_file():
        relpath = scope_path.relative_to(repo_root).as_posix()
        if relpath in excluded_relpaths:
            raise SystemExit(f"Target path is excluded from export scope: {scope_path}")
        collected[relpath] = read_text_file(scope_path)
        return collected

    for path in sorted(scope_path.rglob("*")):
        if not path.is_file() or not should_include_file(path):
            continue
        relpath = path.relative_to(repo_root).as_posix()
        if relpath in excluded_relpaths:
            continue
        collected[relpath] = read_text_file(path)

    if not collected:
        raise SystemExit(f"Target scope contains no exportable files: {scope_path}")
    return collected


def load_snapshot_texts(snapshot_root: Path) -> TextMap:
    """Load all snapshot files as a relative-path map."""
    if not snapshot_root.exists():
        return {}

    collected: TextMap = {}
    for path in sorted(snapshot_root.rglob("*")):
        if not path.is_file() or not should_include_file(path):
            continue
        relpath = path.relative_to(snapshot_root).as_posix()
        collected[relpath] = read_text_file(path)
    return collected


def exclude_relpaths(texts: TextMap, excluded_relpaths: set[str] | None) -> TextMap:
    """Return a copy of the text map without excluded relative paths."""
    if not excluded_relpaths:
        return dict(texts)
    return {path: text for path, text in texts.items() if path not in excluded_relpaths}


def reset_snapshot(snapshot_root: Path, texts: TextMap) -> None:
    """Rewrite the on-disk snapshot for the target scope."""
    if snapshot_root.exists():
        for path in sorted(snapshot_root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
    snapshot_root.mkdir(parents=True, exist_ok=True)

    for relpath, content in texts.items():
        write_text_file(snapshot_root / relpath, content)


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


def build_entry(relpath: str, baseline_text: str | None, current_text: str | None, force_full: bool) -> Dict[str, str]:
    """Build a single file entry for a bundle."""
    if current_text is None:
        return {
            "path": relpath,
            "entry_mode": "delete",
            "base_hash": sha256_text(baseline_text or ""),
            "target_hash": "",
            "payload": "",
        }

    target_hash = sha256_text(current_text)
    if force_full or baseline_text is None:
        return {
            "path": relpath,
            "entry_mode": "full",
            "base_hash": "" if baseline_text is None else sha256_text(baseline_text),
            "target_hash": target_hash,
            "payload": current_text,
        }

    diff_text = build_unified_diff(relpath, baseline_text, current_text)
    if not diff_text:
        raise ValueError(f"No changes detected for {relpath}")

    return {
        "path": relpath,
        "entry_mode": "patch",
        "base_hash": sha256_text(baseline_text),
        "target_hash": target_hash,
        "payload": diff_text,
    }


def build_entries(target_texts: TextMap, baseline_texts: TextMap, force_full: bool) -> List[Dict[str, str]]:
    """Build bundle entries for all changed files in scope."""
    all_paths = sorted(set(target_texts) | set(baseline_texts))
    entries: List[Dict[str, str]] = []

    for relpath in all_paths:
        baseline_text = baseline_texts.get(relpath)
        current_text = target_texts.get(relpath)

        if not force_full and baseline_text == current_text:
            continue

        if force_full and current_text is None:
            continue

        try:
            entries.append(build_entry(relpath, baseline_text, current_text, force_full))
        except ValueError:
            continue

    return entries


def build_bundle(target_relpath: str, target_texts: TextMap, baseline_texts: TextMap, force_full: bool) -> Dict[str, object]:
    """Build bundle metadata and payload."""
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bundle_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    mode = "full" if force_full or not baseline_texts else "patch"
    entries = build_entries(target_texts, baseline_texts, mode == "full")

    if not entries:
        raise SystemExit("No changes detected against the last exported baseline.")

    manifest = {path: sha256_text(text) for path, text in sorted(target_texts.items())}
    return {
        "bundle_version": 2,
        "bundle_id": bundle_id,
        "created_at": created_at,
        "mode": mode,
        "target_path": target_relpath,
        "entry_count": len(entries),
        "manifest": manifest,
        "entries": entries,
    }


def encode_bundle(bundle: Dict[str, object]) -> Dict[str, str]:
    """Serialize, compress, and encode bundle."""
    bundle_json = json.dumps(bundle, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    compressed = gzip.compress(bundle_json.encode("utf-8"))
    encoded = base64.b64encode(compressed).decode("ascii")
    return {
        "bundle_json": bundle_json,
        "compressed_sha256": sha256_bytes(compressed),
        "encoded_payload": encoded,
    }


def chunk_payload(bundle: Dict[str, object], encoded_payload: str, compressed_sha256: str, chunk_size: int) -> str:
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
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Target file or directory to export")
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

    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size must be a positive integer")

    state_dir = repo_root / "tools" / STATE_DIR_NAME
    state_file = state_dir / STATE_FILE_NAME
    snapshot_root = state_dir / SNAPSHOT_ROOT_NAME / target_slug(target_relpath)

    state = load_state(state_file)
    excluded_relpaths: set[str] = set()
    if args.output:
        output_path = Path(args.output).expanduser()
        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()
        try:
            excluded_relpaths.add(output_path.relative_to(repo_root).as_posix())
        except ValueError:
            pass

    target_texts = collect_scope_texts(target_path, repo_root, excluded_relpaths)
    baseline_texts = exclude_relpaths(load_snapshot_texts(snapshot_root), excluded_relpaths)

    bundle = build_bundle(target_relpath, target_texts, baseline_texts, args.full)
    encoded = encode_bundle(bundle)
    chunk_text = chunk_payload(bundle, encoded["encoded_payload"], encoded["compressed_sha256"], args.chunk_size)

    output_path = Path(args.output).resolve() if args.output else None
    if output_path is not None:
        write_text_file(output_path, chunk_text)
        print(f"Wrote chunked bundle to {output_path}")
    else:
        sys.stdout.write(chunk_text)

    reset_snapshot(snapshot_root, target_texts)
    state.update(
        {
            "bundle_version": bundle["bundle_version"],
            "last_bundle_id": bundle["bundle_id"],
            "last_exported_at": bundle["created_at"],
            "last_mode": bundle["mode"],
            "last_target_path": target_relpath,
            "last_entry_count": bundle["entry_count"],
            "last_manifest_size": len(bundle["manifest"]),
        }
    )
    save_state(state_file, state)

    summary = (
        f"bundle_id={bundle['bundle_id']} mode={bundle['mode']} "
        f"target={bundle['target_path']} entries={bundle['entry_count']} "
        f"compressed_sha256={encoded['compressed_sha256']}"
    )
    print(summary, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
