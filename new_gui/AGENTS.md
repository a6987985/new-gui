# Project Guidelines

## Code Architecture

### Package Strategy
- The main entry file is `new_gui/main.py`
- The project now uses a package-based structure under `new_gui/`
- UI components, dialogs, and helper modules may be split into dedicated files under that package

## Code Style

### Language Requirements
- **No Chinese characters** are allowed in the code
- All comments, docstrings, variable names, and strings must be in English
- User-facing messages should be in English
- **Codex should respond in Chinese** when communicating with the user

### General Guidelines
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to public functions and classes
- Keep functions focused and reasonably sized

### Response Requirements
- After every response that changes project files, generate and report a patch bundle for the files changed in that response.
- When generating or reporting a bundle, follow the standard bundle workflow and do not directly provide raw diff content instead of the bundle artifact.
- When generating a transfer bundle for `new_gui/`, write it to `/Users/yangwen/claude_code/new-gui/new_gui/bundle.txt` unless the user explicitly requests a different path.
- When the changed file is a repo-root file such as `AGENTS.md` or `README.md`, generate the patch bundle for that file at `/Users/yangwen/claude_code/new-gui/new_gui/root_bundle.txt` unless the user explicitly requests a different path.
