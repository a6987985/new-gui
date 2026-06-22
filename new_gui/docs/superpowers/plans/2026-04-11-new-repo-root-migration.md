# New Repo Root Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current `new_gui/` directory into the canonical standalone repository root while preserving the `new_gui` Python package name and carrying forward the still-relevant parent-repository assets.

**Architecture:** The migration keeps the package import surface stable by creating a nested `./new_gui/` package inside the current directory and moving the active application code into it. Repository-level assets from the old parent root are then copied or adapted into the current root, followed by verification of imports, smoke coverage, bundle tooling, and standalone Git initialization.

**Tech Stack:** Python 3, PyQt5, `unittest`, shell file moves, Git, GitHub CLI or remote Git workflow

---

## Execution Notes

- Execute this plan **inline in the current workspace**, not in a fresh worktree.
- Reason: the migration target is the current dirty directory itself, and creating a worktree from the parent repository would not preserve the in-progress local state that is being promoted into the new standalone repository.
- Treat parent-root files as source material only. Do not mutate the parent `.git/` metadata to achieve the migration.

## File Structure

### Final root-level files and directories

- Keep: `.gitignore`
- Keep or replace: `AGENTS.md`
- Keep or replace: `CLAUDE.md`
- Create or replace: `README.md`
- Keep: `docs/`
- Create: `tests/`
- Create: `tools/`
- Create: `work_scr/`
- Create: `new_gui/`

### Files moving into the nested package

- Move: `__init__.py` -> `new_gui/__init__.py`
- Move: `main.py` -> `new_gui/main.py`
- Move: `config/` -> `new_gui/config/`
- Move: `services/` -> `new_gui/services/`
- Move: `ui/` -> `new_gui/ui/`
- Move: `tools/governance_smoke.py` -> `new_gui/tools/governance_smoke.py`

### Files copied from the old parent repository

- Copy and adapt: `../README.md` -> `README.md`
- Copy and adapt: `../AGENTS.md` -> `AGENTS.md`
- Copy and adapt: `../CLAUDE.md` -> `CLAUDE.md`
- Copy: `../REFACTOR_ANALYSIS.md` -> `REFACTOR_ANALYSIS.md`
- Copy selected scripts: `../tools/export_patch_bundle.py`, `../tools/import_patch_bundle.py`, `../tools/generate_project_intro_ppt.py` -> `tools/`
- Copy curated docs: `../work_scr/` -> `work_scr/`

### Verification files

- Create: `tests/__init__.py`
- Create: `tests/test_repo_layout.py`

## Task 1: Lock The Target Layout With Regression Tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_repo_layout.py`

- [ ] **Step 1: Write the failing repository-layout test**

```python
from pathlib import Path
import importlib.util
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class RepoLayoutTests(unittest.TestCase):
    def test_nested_package_main_exists(self) -> None:
        self.assertTrue((REPO_ROOT / "new_gui" / "main.py").is_file())

    def test_root_bundle_tool_exists(self) -> None:
        self.assertTrue((REPO_ROOT / "tools" / "export_patch_bundle.py").is_file())

    def test_new_gui_main_is_importable(self) -> None:
        spec = importlib.util.find_spec("new_gui.main")
        self.assertIsNotNone(spec)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the layout test to verify it fails in the current pre-migration state**

Run:

```bash
python3 -m unittest tests.test_repo_layout -v
```

Expected:

- `test_nested_package_main_exists` fails because `new_gui/main.py` does not exist yet
- `test_root_bundle_tool_exists` fails because root `tools/export_patch_bundle.py` does not exist yet
- `test_new_gui_main_is_importable` may fail depending on path resolution

- [ ] **Step 3: Create the test package marker**

```python
# tests package marker
```

- [ ] **Step 4: Re-run the same test command and confirm the failure is still about missing migrated structure, not test packaging**

Run:

```bash
python3 -m unittest tests.test_repo_layout -v
```

Expected:

- test module loads cleanly
- failure remains tied to missing migrated layout

## Task 2: Move Active Application Code Into The Nested `new_gui/` Package

**Files:**
- Create: `new_gui/`
- Modify: root structure by moving `__init__.py`, `main.py`, `config/`, `services/`, `ui/`, `tools/governance_smoke.py`

- [ ] **Step 1: Create the nested package and package tools directory**

Run:

```bash
mkdir -p new_gui
mkdir -p new_gui/tools
```

Expected:

- `new_gui/` exists as a directory under the current root
- `new_gui/tools/` exists for the in-package governance smoke script

- [ ] **Step 2: Move the active code files and directories into the nested package**

Run:

```bash
mv __init__.py new_gui/__init__.py
mv main.py new_gui/main.py
mv config new_gui/config
mv services new_gui/services
mv ui new_gui/ui
mv tools/governance_smoke.py new_gui/tools/governance_smoke.py
```

Expected:

- root code files are gone from the current root
- the moved package files now live under `./new_gui/`

- [ ] **Step 3: Ensure the in-package tools directory is importable**

Run:

```bash
touch new_gui/tools/__init__.py
```

Expected:

- `new_gui/tools/__init__.py` exists

- [ ] **Step 4: Update the governance smoke path assumptions to the new nesting**

Required edits:

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "new_gui"
```

And update any hard-coded output text that still describes the old pre-migration root if needed.

- [ ] **Step 5: Run the repository-layout test and confirm the package-layout checks are fixed**

Run:

```bash
python3 -m unittest tests.test_repo_layout -v
```

Expected:

- `test_nested_package_main_exists` passes
- `test_new_gui_main_is_importable` passes
- `test_root_bundle_tool_exists` still fails until Task 3 copies the root bundle tool

## Task 3: Recreate The New Repository Root Assets

**Files:**
- Create or replace: `.gitignore`
- Create or replace: `AGENTS.md`
- Create or replace: `CLAUDE.md`
- Create or replace: `README.md`
- Create: `REFACTOR_ANALYSIS.md`
- Create: `tools/export_patch_bundle.py`
- Create: `tools/import_patch_bundle.py`
- Create: `tools/generate_project_intro_ppt.py`
- Create: `work_scr/*`

- [ ] **Step 1: Create the root support directories**

Run:

```bash
mkdir -p tools
mkdir -p work_scr
```

Expected:

- root `tools/` exists
- root `work_scr/` exists

- [ ] **Step 2: Copy the repository-level files from the old parent root**

Run:

```bash
cp ../AGENTS.md ./AGENTS.md
cp ../CLAUDE.md ./CLAUDE.md
cp ../README.md ./README.md
cp ../REFACTOR_ANALYSIS.md ./REFACTOR_ANALYSIS.md
cp ../tools/export_patch_bundle.py ./tools/export_patch_bundle.py
cp ../tools/import_patch_bundle.py ./tools/import_patch_bundle.py
cp ../tools/generate_project_intro_ppt.py ./tools/generate_project_intro_ppt.py
rsync -a --exclude '__pycache__' ../work_scr/ ./work_scr/
```

Expected:

- root repository assets now exist in the new root
- no parent cache files are copied

- [ ] **Step 3: Merge the old parent `.gitignore` with the current root OMX ignore rules**

Required content after merge must include both families of rules:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
*.egg

# Virtual environments
venv/
env/
.venv/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# Logs
*.log

# Local test data
mock_runs/

# Bundle tool local state
tools/.patch_bundle_state/

# OMX local runtime files
.omx/
.codex/*
!.codex/agents/
!.codex/agents/**
!.codex/skills/
!.codex/skills/**
.codex/skills/.system/**
!.codex/prompts/
!.codex/prompts/**
```

- [ ] **Step 4: Verify the required root assets exist**

Run:

```bash
ls AGENTS.md CLAUDE.md README.md REFACTOR_ANALYSIS.md tools/export_patch_bundle.py tools/import_patch_bundle.py
```

Expected:

- all listed files print successfully

## Task 4: Adapt Documentation And Paths To The New Root Layout

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `REFACTOR_ANALYSIS.md`
- Modify: selected `work_scr/*.md`

- [ ] **Step 1: Update the repository tree in `README.md` to the new root structure**

Required structural content:

```text
<repo root>/
├── new_gui/
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   ├── services/
│   ├── ui/
│   └── tools/
├── tools/
├── work_scr/
├── README.md
├── AGENTS.md
├── CLAUDE.md
└── .gitignore
```

- [ ] **Step 2: Replace stale entry-point references**

Run:

```bash
rg -n "reproduce_ui\\.py|python new_gui/reproduce_ui.py|Main application file" README.md AGENTS.md CLAUDE.md REFACTOR_ANALYSIS.md work_scr
```

Then update the relevant references so they consistently point at:

```text
new_gui/main.py
python new_gui/main.py
```

- [ ] **Step 3: Update bundle instructions to the new standalone-root semantics**

Required README examples should use the new root-local paths:

```bash
python tools/export_patch_bundle.py --target new_gui --output bundle.txt
python tools/export_patch_bundle.py --target README.md --output root_bundle.txt
```

And any absolute path instructions must resolve under the current directory, not the old parent root.

- [ ] **Step 4: Re-scan the migrated docs for stale parent-root assumptions**

Run:

```bash
rg -n "/Users/yangwen/claude_code/new-gui|reproduce_ui\\.py|new-gui/" README.md AGENTS.md CLAUDE.md REFACTOR_ANALYSIS.md work_scr
```

Expected:

- only intentional historical references remain
- no active instruction points to the old parent-root execution model

## Task 5: Re-Verify Runtime And Tooling From The New Root

**Files:**
- Modify: any files still needed to satisfy runtime verification

- [ ] **Step 1: Verify the nested package is importable from the new root**

Run:

```bash
python3 - <<'PY'
import importlib
module = importlib.import_module("new_gui.main")
print(module.__name__)
PY
```

Expected:

- prints `new_gui.main`

- [ ] **Step 2: Run the governance smoke test from the new root layout**

Run:

```bash
python3 new_gui/tools/governance_smoke.py
```

Expected:

- smoke script exits 0
- final output reports successful compilation under `new_gui/`

- [ ] **Step 3: Verify the migrated root bundle tool is callable**

Run:

```bash
python3 tools/export_patch_bundle.py --help
```

Expected:

- help text prints successfully

- [ ] **Step 4: Verify the new root can generate a package-target bundle**

Run:

```bash
python3 tools/export_patch_bundle.py --target new_gui --output bundle.txt
```

Expected:

- bundle metadata prints successfully
- root `bundle.txt` is refreshed by the migrated root tool

## Task 6: Establish The Current Directory As A Standalone Git Repository

**Files:**
- Create: `.git/` under the current root if not already initialized
- Modify: local Git metadata and remote configuration

- [ ] **Step 1: Confirm whether the current directory already has its own Git metadata**

Run:

```bash
test -d .git && echo HAS_GIT || echo NO_GIT
```

Expected:

- likely `NO_GIT` before standalone initialization

- [ ] **Step 2: Initialize the standalone repository at the current root**

Run:

```bash
git init
git branch -M main
```

Expected:

- current directory now has its own `.git/`
- branch name is `main`

- [ ] **Step 3: Inspect the standalone repository contents before first commit**

Run:

```bash
git status --short
```

Expected:

- status shows only files intended for the new standalone repository

- [ ] **Step 4: Create the initial standalone-repo commit**

Run:

```bash
git add .
git commit -m "Restructure project as standalone new_gui repository"
```

Expected:

- commit succeeds in the new standalone repository

- [ ] **Step 5: Create and connect the new GitHub repository**

Preferred command if `gh` is installed and authenticated:

```bash
gh repo create <new-repo-name> --private --source=. --remote=origin --push
```

Fallback remote flow:

```bash
git remote add origin <new-github-url>
git push -u origin main
```

Expected:

- current directory is published as the new canonical GitHub repository

## Task 7: Final Verification Sweep

**Files:**
- Modify: any remaining stragglers found during verification

- [ ] **Step 1: Run the full repository-layout and smoke verification set**

Run:

```bash
python3 -m unittest tests.test_repo_layout -v
python3 new_gui/tools/governance_smoke.py
python3 tools/export_patch_bundle.py --help
git status --short
```

Expected:

- layout test passes
- governance smoke passes
- bundle tool help succeeds
- git status is clean or contains only intentional generated bundle outputs

- [ ] **Step 2: Refresh transfer bundles for the migrated standalone repository**

Run:

```bash
python3 tools/export_patch_bundle.py --target new_gui --output bundle.txt
python3 tools/export_patch_bundle.py --target README.md --output root_bundle.txt
```

Expected:

- both bundle files refresh successfully under the new root

- [ ] **Step 3: Commit the final verification adjustments if needed**

Run:

```bash
git add .
git commit -m "Finalize standalone repository migration verification"
```

Expected:

- only needed if verification fixes were required after the initial migration commit
