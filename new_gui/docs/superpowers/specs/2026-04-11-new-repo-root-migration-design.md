# New Repo Root Migration Design

**Date:** 2026-04-11

## Goal

Promote the current `new_gui/` directory to become the root of a new standalone repository, while preserving the Python package name `new_gui` and carrying forward the still-relevant repository-level files from the old parent repository.

## Context

The current filesystem layout has two layers:

- Old repository root: `/Users/yangwen/claude_code/new-gui`
- Current code directory that should become the new repository root: `/Users/yangwen/claude_code/new-gui/new_gui`

Today, the active application code already lives in the lower directory, but imports still assume a package named `new_gui`, for example `from new_gui.services import ...`. That means the new standalone repository cannot simply keep the current files at the top level without breaking imports. The package boundary must remain explicit.

## Approved Direction

Use the current directory as the new repository root, and preserve `new_gui` as the package name by moving the current codebase into a new `./new_gui/` package directory inside that root.

This keeps the runtime import surface stable and makes the repository structure conventional for Python:

- repository root contains repository metadata and tooling
- `new_gui/` contains application code
- documentation and helper scripts live at the root

## Target Repository Structure

```text
<new repo root>/
  .gitignore
  AGENTS.md
  CLAUDE.md
  README.md
  docs/
  tools/
  work_scr/
  new_gui/
    __init__.py
    main.py
    config/
    services/
    ui/
    tools/
```

Additional OMX local files may remain in the root for local workflows:

- `.codex/`
- `.omx/`

Those are local runtime assets, not part of the published project structure contract.

## Migration Scope

### 1. Code relocation

Move the current application files from the current root into a new package directory:

- current root `main.py` -> `new_gui/main.py`
- current root `config/` -> `new_gui/config/`
- current root `services/` -> `new_gui/services/`
- current root `ui/` -> `new_gui/ui/`
- current root `tools/governance_smoke.py` -> `new_gui/tools/governance_smoke.py`
- current root `__init__.py` remains as `new_gui/__init__.py`

Any path-sensitive scripts must be updated to reflect the additional directory level.

### 2. Repository-level file migration

Move or recreate the still-relevant parent-repository files at the new root:

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- top-level `tools/` scripts that support bundle export/import or project maintenance
- selected `work_scr/` documents that remain useful

Do not carry over old repository internals such as:

- parent `.git/`
- obsolete bundles
- cache directories
- stale generated artifacts

### 3. Documentation adaptation

Update all repository-facing documentation to the new structure:

- entry path examples
- bundle paths
- execution commands
- tree diagrams
- references to the old parent repository layout

### 4. GitHub representation

Express the migration as a new Git repository rooted at the current directory after restructuring.

That means:

- initialize or re-root Git at the new repository root
- ensure the new root contains the intended published files only
- connect the new root to a new GitHub repository
- push the migrated structure as the canonical history for the new project

Preserving old parent-repo Git history is not required for this migration unless explicitly requested later.

## Why This Design

### Keep the package name

The codebase currently imports through `new_gui.*` everywhere. Preserving the package name avoids a noisy, high-risk import rewrite across the entire application.

### Make the repository root conventional

A standalone repository should expose repository-level files at the top and keep application code under a clear package directory. The current nested arrangement is operationally confusing and makes GitHub presentation misleading.

### Separate migration from refactoring

This migration should fix repository boundaries and project shape first. It should not simultaneously redesign module ownership or do broad architecture cleanup.

## Non-Goals

The migration will not, by itself:

- rename the Python package away from `new_gui`
- refactor `MainWindow` ownership boundaries
- clean every historical document under `work_scr/`
- preserve the old repository as the main publishing root

## Execution Phases

### Phase 1: Prepare the new root

- create the new `new_gui/` package directory inside the current root
- move active application code into that package
- update path-sensitive files and smoke tooling

### Phase 2: Bring over repository assets

- copy or rewrite parent-root files into the new root
- update README and instruction files to the new structure
- keep only relevant support tooling

### Phase 3: Re-establish verification

- ensure imports resolve from the new root
- run the governance smoke test from the new root layout
- verify bundle tooling still writes to the intended paths

### Phase 4: Publish as a new GitHub repository

- initialize or refresh Git metadata in the new root
- inspect repository contents carefully
- add the new GitHub remote
- commit and push the migrated repository

## Verification Requirements

The migration is complete only when all of the following are true:

1. Running from the new root can import `new_gui.main`
2. The main entry path documented by the repository is correct
3. `tools/governance_smoke.py` still passes after path updates
4. Bundle export still targets the correct files and output paths
5. The new GitHub repository reflects the migrated structure without depending on the old parent root

## Risks

### Path breakage

Files such as smoke tools and documentation currently assume the old nesting. These must be updated carefully.

### Tooling drift

Bundle scripts and local OMX files may still carry assumptions about the old root. Verification must explicitly cover them.

### Mixed migration scope

The old parent repository contains useful files and obsolete files side by side. Selection must stay intentional so stale artifacts do not become part of the new standalone repository.

## Recommended Follow-Up

After this design is approved in writing, create a task-by-task implementation plan for the migration, then execute the migration in small verified steps.
