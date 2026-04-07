"""Helpers for loading sidebar categories from bb.tcl."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple


_CATEGORY_LINE_RE = re.compile(r'^\s*([A-Za-z0-9_./-]+)\s+"([^"]*)"\s*$')


def load_bb_tcl_categories(run_dir: str, file_name: str = "bb.tcl") -> Tuple[List[Dict[str, object]], str]:
    """Load category definitions from one bb.tcl file under the active run directory."""
    file_path = os.path.join(run_dir or "", file_name)
    if not run_dir or not os.path.isfile(file_path):
        return [], file_path

    categories: List[Dict[str, object]] = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            match = _CATEGORY_LINE_RE.match(line)
            if not match:
                continue

            category_name = match.group(1).strip()
            target_blob = match.group(2).strip()
            targets = [token for token in target_blob.split() if token]
            if not category_name:
                continue

            categories.append(
                {
                    "id": category_name.lower(),
                    "label": category_name,
                    "targets": targets,
                }
            )

    return categories, file_path
