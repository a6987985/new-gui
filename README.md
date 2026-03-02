# XMeta Console GUI

A PyQt5-based GUI monitoring tool for tracking task execution status and dependencies in EDA/chip design workflows.

## Project Structure

```
new-gui/
├── reproduce_ui.py    # Main application file (~4400 lines)
├── README.md          # This documentation file
├── .cursorrules       # Cursor editor rules configuration
├── .gitignore         # Git ignore rules
└── .claude/           # Claude Code configuration
```

## Technology Stack

- **GUI Framework**: PyQt5
- **Python Version**: 3.10+
- **Concurrency**: `ThreadPoolExecutor` for background tasks
- **File Monitoring**: `QFileSystemWatcher` for real-time status updates

## Features

### 1. Target Status Monitoring

- Parse `.target_dependency.csh` files to build target dependency trees
- Display hierarchical view with levels, targets, status, and timestamps
- Real-time status updates via file system watcher (no polling)
- Status colors with visual feedback

### 2. Status Types and Visual Indicators

| Status | Color | Animation | Description |
|--------|-------|-----------|-------------|
| `finish` | PaleGreen (#98FB98) | None | Task completed successfully |
| `running` | Yellow (#FFFF00) | Pulse | Task currently running |
| `failed` | Light Red (#FF9999) | None | Task failed |
| `skip` | PeachPuff (#FFDAB9) | None | Task skipped |
| `scheduled` | Deep Blue (#4A90D9) | None | Task scheduled |
| `pending` | Orange (#FFA500) | None | Task pending |
| (no status) | Light Blue (#88D0EC) | None | Status not yet determined |

### 3. Dependency Tracing

- **Trace Up**: Find all upstream dependencies (inputs)
- **Trace Down**: Find all downstream dependencies (outputs)
- Visual filtering to show only related targets
- **Dependency Graph**: Interactive visualization with:
  - Node selection and highlighting
  - Upstream/downstream path tracing
  - Zoom, pan, and fit-to-view controls
  - Export to PNG

### 4. Search and Filter

- Real-time search by target name
- Status-based filtering
- Dependency-based filtering

### 5. Tune File Management

Tune files are TCL scripts used for task configuration.

#### Naming Convention
```
{run_dir}/tune/{target}.{suffix}.tcl
```

Example: `/path/to/run/tune/synthesis.pre_opt.tcl`

#### Operations
- **Open Tune**: Open tune file with gvim (supports multiple tune files per target)
- **Copy Tune To...**: Copy tune file to multiple runs

### 6. Context Menu Actions

Right-click on a target to access organized menu:

**▶ Execute**
- Run All / Run Selected
- Stop
- Skip / Unskip
- Invalid

**📁 Files**
- Terminal (open in run directory)
- csh (shell script)
- Log (log file)
- cmd (command file)

**🎵 Tune**
- Open Tune
- Copy Tune To...

**🔗 Trace**
- Trace Up (Ctrl+U)
- Trace Down (Ctrl+D)
- Dependency Graph (Ctrl+G)

**📋 Copy**
- Copy Target Name (Ctrl+C)
- Copy Run Path

### 7. Theme System

Three themes available:
- **Light Theme** (default): Clean, bright interface
- **Dark Theme**: Reduced eye strain for low-light environments
- **High Contrast**: Enhanced readability

Access via `View → Theme` menu or `Ctrl+T` shortcut.

### 8. Status Bar

Bottom status bar displays:
- Current run name
- Task statistics by status (with colored icons)
- Connection status indicator
- Current theme indicator

### 9. Notifications

Toast notifications appear in bottom-right corner:
- **Info** (blue): General information
- **Success** (green): Successful operations
- **Warning** (yellow): Warnings
- **Error** (red): Errors

Auto-dismiss after configurable duration, click to close.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Focus search field |
| `Ctrl+R` | Refresh current view |
| `Ctrl+E` | Expand all items |
| `Ctrl+W` | Collapse all items |
| `Ctrl+T` | Toggle theme |
| `Ctrl+G` | Show dependency graph |
| `Ctrl+C` | Copy selected target name |
| `Ctrl+Enter` | Run selected targets |
| `Ctrl+U` | Trace upstream dependencies |
| `Ctrl+D` | Trace downstream dependencies |

## Core Classes

| Class | Description |
|-------|-------------|
| `MainWindow` | Main application window |
| `ThemeManager` | Singleton managing application themes |
| `StatusAnimator` | Manages status animations (pulse effect) |
| `NotificationWidget` | Individual notification popup |
| `NotificationManager` | Manages notification stacking and display |
| `StatusBar` | Bottom status bar with statistics |
| `BorderItemDelegate` | Custom delegate for row borders and bold text on hover/selection |
| `DependencyGraphDialog` | Interactive dependency graph viewer |
| `InteractiveNodeItem` | Clickable node for graph |
| `TreeViewEventFilter` | Event filter for expand/collapse handling |
| `ColorTreeView` | Custom tree view with colored backgrounds |
| `BoundedComboBox` | ComboBox with search functionality |
| `SelectTuneDialog` | Dialog for selecting a tune file |
| `CopyTuneDialog` | Dialog for selecting runs to copy tune to |
| `CopyTuneSelectDialog` | Combined dialog for tune copy operations |

## Data Sources

### Status Files
```
{run_dir}/status/{target}.{status}
```
The latest status file (by mtime) determines the current status.

### Time Tracking
```
{run_dir}/logs/targettracker/{target}.start
{run_dir}/logs/targettracker/{target}.finished
```
File modification times are used for start/end timestamps.

### Dependency Information
```
{run_dir}/.target_dependency.csh
```
Contains `ACTIVE_TARGETS`, `LEVEL_N`, `TARGET_LEVEL_*`, `DEPENDENCY_OUT_*`, and `ALL_RELATED_*` definitions.

## Configuration

### Status Configuration
```python
STATUS_CONFIG = {
    "finish": {"color": "#98FB98", "icon": "✓", "animation": None, "text_color": "#1a5f1a"},
    "running": {"color": "#FFFF00", "icon": "▶", "animation": "pulse", "text_color": "#333333"},
    "failed": {"color": "#FF9999", "icon": "✗", "animation": None, "text_color": "#8b0000"},
    "pending": {"color": "#FFA500", "icon": "◇", "animation": None, "text_color": "#333333"},
    "": {"color": "#88D0EC", "icon": "", "animation": None, "text_color": "#1a4f6f"},
    # ...
}
```

### Theme Configuration
```python
THEMES = {
    "light": {
        "window_bg": "qlineargradient(...)",
        "tree_bg": "rgba(255, 255, 255, 0.9)",
        "text_color": "#333333",
        "accent_color": "#4A90D9",
        # ...
    },
    "dark": { ... },
    "high_contrast": { ... }
}
```

### Shortcut Configuration
```python
SHORTCUTS = {
    "search": {"key": "Ctrl+F", "description": "Focus search field"},
    "refresh": {"key": "Ctrl+R", "description": "Refresh current view"},
    "expand_all": {"key": "Ctrl+E", "description": "Expand all items"},
    # ...
}
```

### Column Widths
| Column | Width |
|--------|-------|
| Level | 80px (fixed) |
| Target | 480px (fixed) |
| Status | Dynamic (based on longest status text) |
| Tune | 150px (fixed) |
| Start Time | 140px (based on time format) |
| End Time | 140px (based on time format) |

### Pre-compiled Regex Patterns
- `RE_LEVEL_LINE`: Parse level definitions
- `RE_ACTIVE_TARGETS`: Parse active targets list
- `RE_TARGET_LEVEL`: Parse target level assignments
- `RE_DEPENDENCY_OUT`: Parse output dependencies
- `RE_ALL_RELATED`: Parse related targets

## Performance Optimizations

1. **Status Caching**: Batch status lookups with `_build_status_cache()`
2. **File System Watcher**: Replaces polling timer for status updates
3. **Debounce Timer**: 300ms delay to batch rapid file changes
4. **In-place Updates**: Refresh status without rebuilding entire tree
5. **Animation Timer**: 20 FPS animation update for running status
6. **Delegate Drawing**: Custom delegate for efficient row rendering
7. **Code Optimization**: Removed unused classes and imports (~9% code reduction)

## Usage

```bash
python reproduce_ui.py
```

## Requirements

- Python 3.10+
- PyQt5
- gvim (optional, for opening tune files)

## Changelog

### v2.0.0 - UI Enhancement Release

#### New Features
- **Theme System**: Light, Dark, and High Contrast themes (Ctrl+T to toggle)
- **Keyboard Shortcuts**: Full keyboard navigation support
- **Status Bar**: Real-time task statistics at bottom of window
- **Notification System**: Toast notifications for user feedback
- **Enhanced Dependency Graph**: Interactive nodes, path highlighting, export to PNG
- **Grouped Context Menu**: Organized menus with icons and shortcuts
- **Bold Text on Selection/Hover**: Improved visual feedback in tree view
- **Dynamic Status Column Width**: Auto-calculated based on status text

#### Improvements
- Optimized tree view delegate rendering
- Enhanced file monitoring performance
- Improved user experience feedback
- Better visual hierarchy and organization
- Code optimized by removing unused components (~9% smaller)

#### Internal Changes
- Added `ThemeManager` singleton for theme management
- Added `StatusAnimator` for animation coordination
- Added `NotificationManager` for notification display
- Enhanced `BorderItemDelegate` with bold text on hover/selection
- Enhanced `DependencyGraphDialog` with interactive features
- Removed unused `HoverInfoCard` and `AdvancedSearchPanel` classes

## License

Internal use only.
