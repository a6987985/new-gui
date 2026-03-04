# XMeta Console GUI

A PyQt5-based GUI monitoring tool for tracking task execution status and dependencies in EDA/chip design workflows.

## Project Structure

```
new-gui/
├── reproduce_ui.py    # Main application file (~5590 lines)
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

| Status | Color | Icon | Animation | Description |
|--------|-------|------|-----------|-------------|
| `finish` | PaleGreen (#98FB98) | ✓ | None | Task completed successfully |
| `running` | Yellow (#FFFF00) | ▶ | Pulse | Task currently running |
| `failed` | Light Red (#FF9999) | ✗ | None | Task failed |
| `skip` | PeachPuff (#FFDAB9) | ○ | None | Task skipped |
| `scheduled` | Deep Blue (#4A90D9) | ◷ | None | Task scheduled |
| `pending` | Orange (#FFA500) | ◇ | None | Task pending |
| (no status) | Light Blue (#88D0EC) | | None | Status not yet determined |

#### Row Visual Effects
- **Hover**: Semi-transparent blue background (#E6F0FF), bold text
- **Selected**: Gray background (#C0C0BE), bold text
- **Row Borders**: Drawn on hover/selection for visual clarity

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
{run_dir}/tune/{target}/{target}.{suffix}.tcl
```

Example: `/path/to/run/tune/synthesis/synthesis.pre_opt.tcl`

#### Operations
- **Open Tune**: Open tune file with gvim (supports multiple tune files per target)
  - Via context menu: Right-click → Tune → Open Tune
  - Via double-click: Double-click on the Tune column cell to show dropdown menu
- **Copy Tune To...**: Copy tune file to multiple runs (supports selecting multiple tune files)

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
- Copy Run Path (single target only)

**⚙ Params**
- User Params (Ctrl+P)
- Tile Params (Ctrl+Shift+P)

### 7. Status Overview

Access via `Status → Show All Status` menu to view a summary of all run directories:
- Displays: Run Directory, Latest Target, Status, Time Stamp
- Double-click any row to copy the run name to clipboard
- Provides quick overview of all runs in the base directory

### 8. Embedded Search Filter

Double-click on the Target column header to show an embedded search input:
- Real-time filtering as you type
- Press Escape or Enter to hide the filter
- Shows flat list of matching targets

### 9. BSUB Parameter Editing

Double-click on Queue, Cores, or Memory columns to edit bsub parameters:
- **Queue**: BSUB queue name (-q parameter)
- **Cores**: Number of CPU cores (-n parameter, must be numeric)
- **Memory**: Memory allocation in MB (rusage[mem=XXX], must be numeric)
- Changes are saved directly to `{run_dir}/make_targets/{target}.csh`

### 10. Tab Label Interaction

The tab label (showing current run name) supports:
- **Double-click**: Toggle between Expand All and Collapse All
- Displays trace mode status (red text) when tracing dependencies

### 11. Theme System

Three themes available:
- **Light Theme** (default): Clean, bright interface
- **Dark Theme**: Reduced eye strain for low-light environments
- **High Contrast**: Enhanced readability

Access via `View → Theme` menu or `Ctrl+T` shortcut.

### 12. Status Bar

Bottom status bar displays:
- Current run name
- Task statistics by status (with colored icons)
- Connection status indicator
- Current theme indicator

### 13. Notifications

Toast notifications appear in bottom-right corner:
- **Info** (blue): General information
- **Success** (green): Successful operations
- **Warning** (yellow): Warnings
- **Error** (red): Errors

Auto-dismiss after configurable duration, click to close.

### 14. Params Editor

Edit and view parameter files for each run.

#### File Locations
```
{run_dir}/user.params   # User-modifiable parameters (editable)
{run_dir}/tile.params   # All parameters used (read-only)
```

#### File Format
```
# Comment lines start with #
VARA = 111
VARB = "value with spaces"
VARC = 333
```

#### User Params Features
- **Add**: Create new parameters
- **Edit**: Modify existing parameter values
- **Delete**: Remove parameters
- **Search**: Filter parameters by name (with debounce for large files)
- **Save**: Write changes to file (auto-backup to .bak)
- **Gen Params**: Execute `XMeta_gen_params` to generate params to flow

#### Tile Params Features
- **View**: Read-only parameter list
- **Search**: Filter parameters by name
- **Copy**: Double-click to copy parameter to clipboard

#### Access Methods
- **Menu**: Tools → User Params / Tile Params
- **Context Menu**: Right-click → Params → User Params / Tile Params
- **Shortcuts**: Ctrl+P / Ctrl+Shift+P

### 15. Multi-Selection Support

The tree view supports extended selection for batch operations:
- **Ctrl+Click**: Add/remove individual items from selection
- **Shift+Click**: Select range of items
- Actions (Run, Stop, Skip, Unskip, Invalid) apply to all selected targets
- Copy (Ctrl+C) copies all selected target names to clipboard

### 16. Run Selection with Search

The run dropdown (BoundedComboBox) provides:
- **Search Mode**: Click the 🔍 button to enable text filtering
- **Auto-complete**: Type to filter available runs
- **Smart Positioning**: Popup stays within window bounds
- **Current Selection First**: Selected run appears at top of list when opened

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
| `Ctrl+P` | Open user.params editor |
| `Ctrl+Shift+P` | View tile.params |

## Core Classes

| Class | Description |
|-------|-------------|
| `MainWindow` | Main application window (~2800 lines) |
| `ThemeManager` | Singleton managing application themes |
| `StatusAnimator` | Singleton managing status animations (pulse effect) |
| `NotificationWidget` | Individual notification popup |
| `NotificationManager` | Singleton managing notification stacking and display |
| `StatusBar` | Bottom status bar with statistics |
| `BorderItemDelegate` | Custom delegate for row borders, status colors, and bold text on hover/selection |
| `FilterHeaderView` | Custom header with embedded search input for Target column |
| `TuneComboBoxDelegate` | ComboBox delegate for Tune column dropdown |
| `TreeViewEventFilter` | Event filter for expand/collapse handling |
| `RoundedScrollBar` | Custom scrollbar with rounded corners (cross-platform) |
| `ColorTreeView` | Custom tree view with custom branch drawing and rounded scrollbars |
| `BoundedComboBox` | ComboBox with search functionality and bounded popup positioning |
| `ClickableLabel` | QLabel that emits doubleClicked signal |
| `ParamsTableModel` | High-performance QAbstractTableModel for params data with filtering |
| `ParamsEditorDialog` | Dialog for editing user.params and viewing tile.params |
| `DependencyGraphDialog` | Interactive dependency graph viewer with zoom/pan/export |
| `InteractiveNodeItem` | Clickable/hoverable node for dependency graph |
| `SelectTuneDialog` | Dialog for selecting a single tune file |
| `CopyTuneDialog` | Dialog for selecting runs to copy tune to |
| `CopyTuneSelectDialog` | Combined dialog for multi-tune selection and multi-run copy |

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

### BSUB Parameters
```
{run_dir}/make_targets/{target}.csh
```
Shell scripts containing BSUB job submission parameters:
- `-q <queue>`: Queue name
- `-n <cores>`: Number of CPU cores
- `-R "rusage[mem=<MB>]"`: Memory allocation

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
| Target | 400px (fixed) |
| Status | Dynamic (based on longest status text + 20px padding) |
| Tune | 120px (fixed) |
| Start Time | Dynamic (based on time format "YYYY-MM-DD HH:MM:SS" + 20px) |
| End Time | Dynamic (based on time format "YYYY-MM-DD HH:MM:SS" + 20px) |
| Queue | 100px (fixed) |
| Cores | 60px (fixed) |
| Memory | 80px (fixed) |

### Tree View Columns

The tree view displays the following columns:
- **Level**: Task level in the dependency hierarchy
- **Target**: Task name
- **Status**: Current task status (with color coding)
- **Tune**: Available tune file suffixes (double-click to open dropdown)
- **Start Time**: Task start timestamp
- **End Time**: Task end timestamp
- **Queue**: BSUB queue name (double-click to edit)
- **Cores**: Number of CPU cores (double-click to edit)
- **Memory**: Memory allocation in MB (double-click to edit)

### Pre-compiled Regex Patterns
- `RE_LEVEL_LINE`: Parse level definitions
- `RE_ACTIVE_TARGETS`: Parse active targets list
- `RE_TARGET_LEVEL`: Parse target level assignments
- `RE_DEPENDENCY_OUT`: Parse output dependencies
- `RE_ALL_RELATED`: Parse related targets
- `RE_PARAM_LINE`: Parse parameter file lines (VAR = value)

## Performance Optimizations

1. **Status Caching**: Batch status lookups with `_build_status_cache()` - reads all status files in one pass
2. **Time Caching**: Batch timestamp lookups cached alongside status
3. **File System Watcher**: `QFileSystemWatcher` replaces polling timer for real-time status updates
4. **Debounce Timer**: 300ms delay to batch rapid file changes before UI refresh
5. **Backup Timer**: 10-second fallback refresh in case file watcher misses events
6. **In-place Updates**: Refresh status/time without rebuilding entire tree when possible
7. **Animation Timer**: 20 FPS (50ms interval) for running status pulse animation
8. **Delegate Drawing**: Custom `BorderItemDelegate` for efficient row rendering with visual effects
9. **Virtualized Params Table**: `ParamsTableModel` uses `QAbstractTableModel` for large params files
10. **Search Debounce**: 200ms debounce in params editor search to avoid lag on large files
11. **ThreadPoolExecutor**: Background threads for file operations (gvim, terminal, commands)

## Usage

```bash
python reproduce_ui.py
```

## Requirements

- Python 3.10+
- PyQt5
- gvim (optional, for opening tune files)

## Changelog

### v2.4.0 - Code Cleanup and Documentation

#### Code Improvements
- **Single File Architecture**: Complete application in ~5590 lines
- **Organized Imports**: Standard library, PyQt5, and local imports properly grouped
- **Pre-compiled Regex**: All regex patterns compiled at module level for performance
- **Singleton Pattern**: `ThemeManager`, `StatusAnimator`, `NotificationManager` use proper singleton pattern

#### Documentation Updates
- Updated column widths to match actual code values
- Added BSUB Parameters data source documentation
- Added row visual effects (hover/selection) description
- Added multi-selection support documentation
- Added run selection with search documentation
- Updated Core Classes table with accurate descriptions
- Expanded Performance Optimizations section

### v2.3.0 - Cross-Platform UI Fixes

#### New Features
- **Rounded Scrollbar**: Custom scrollbar with rounded corners for all platforms
  - Works consistently across macOS and Linux (CentOS 7)
  - Custom QPainter-based rendering bypasses platform-specific QSS limitations
  - Supports hover and pressed color states
  - Theme-aware color updates
- **Custom ComboBox Dropdown Arrow**: Double-V arrow icon for dropdown indicator
  - Custom QPainter rendering for cross-platform consistency
  - SVG-style rounded line caps and joins
  - Hover color feedback

#### Improvements
- Fixed scrollbar rounded corners not displaying on Linux
- Fixed ComboBox dropdown arrow not visible on Linux
- Platform-independent UI components using manual paint events
- **Removed duplicate toolbar buttons**: Removed second row of buttons (Terminal, CSH, Log, CMD, Trace Up, Trace Down) as these functions are already available via right-click context menu and keyboard shortcuts, making the UI more compact

### v2.2.0 - Feature Enhancements

#### New Features
- **BSUB Parameter Columns**: Added Queue, Cores, Memory columns to tree view
  - Double-click to edit bsub parameters in csh files
  - Validation for numeric inputs
- **Status Overview**: New `Status → Show All Status` menu for viewing all runs at a glance
  - Shows run directory, latest target, status, and timestamp
  - Double-click to copy run name
- **Embedded Search Filter**: Double-click Target column header to show inline search
  - Real-time filtering with flat result display
- **Tune Column Dropdown**: Double-click Tune column to show dropdown menu
  - Direct access to open tune files
- **Copy Run Path**: Context menu action to copy current run path (single target)
- **Gen Params Button**: User Params Editor now includes "Gen Params" button
  - Executes `XMeta_gen_params` command
  - Prompts to save if params modified
- **Tab Label Double-Click**: Double-click tab label to toggle expand/collapse all
- **Params Table Performance**: New `ParamsTableModel` using `QAbstractTableModel`
  - Virtualized rendering for large params files
  - Debounced search (200ms delay)

#### Improvements
- Tune file path corrected to `{run_dir}/tune/{target}/{target}.{suffix}.tcl`
- Copy Tune dialog now supports selecting multiple tune files
- Improved params editor with better context menu

### v2.1.0 - Params Editor Feature

#### New Features
- **Params Editor**: Edit user.params and view tile.params
  - Add, edit, delete parameters
  - Search/filter functionality
  - Auto-backup on save
  - Read-only mode for tile.params
- **Tools Menu**: New menu for parameter file access
- **Context Menu**: Params submenu in right-click menu

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
