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
- **Codex should respond in Chinese** when communicating with the user

### General Guidelines
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to public functions and classes
- Keep functions focused and reasonably sized

### Response Requirements
- At the end of every assistant response, add a final item showing the current total Python code size for this project.
- Measure code size as total `.py` lines under `new_gui/`, excluding caches such as `__pycache__/`.
