# Project Guidelines

## Code Architecture

### Package Strategy
- The main entry file is `new_gui/reproduce_ui.py`
- The project now uses a package-based structure under `new_gui/`
- UI components, dialogs, and helper modules may be split into dedicated files under that package

## Code Style

### Language Requirements
- **No Chinese characters** are allowed in the code
- All comments, docstrings, variable names, and strings must be in English
- User-facing messages should be in English
- **Claude should respond in Chinese** when communicating with the user

### General Guidelines
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to public functions and classes
- Keep functions focused and reasonably sized
- When generating a transfer bundle for `new_gui/`, write it to `/Users/yangwen/claude_code/new-gui/new_gui/bundle.txt` unless the user explicitly requests a different path.
- When the changed file is a repo-root file such as `AGENTS.md` or `README.md`, write that bundle to `/Users/yangwen/claude_code/new-gui/new_gui/root_bundle.txt` unless the user explicitly requests a different path.
