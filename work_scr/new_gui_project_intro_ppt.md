# New-GUI Function And Operation PPT

## Slide 1. Title

**New-GUI for XMeta Flow**

Function Overview And User Operation Guide

- Project: `new-gui`
- Main entry: `reproduce_ui.py`
- Target usage: daily run monitoring and target operation

Speaker notes:
This deck is focused on what the tool does and how to use it in daily work, rather than project background or implementation details.

---

## Slide 2. What New-GUI Is Used For

**Main purpose**

- Monitor run and target execution status in one window
- View dependency hierarchy and trace upstream or downstream targets
- Open related files quickly, including log, cmd, csh, tune, and params
- Perform common target actions without switching back to terminal commands

Speaker notes:
The tool is a practical operation console on top of the existing flow directory structure.

---

## Slide 3. Main Interface Layout

**Main screen areas**

- Menu bar: Status, View, Tools
- Top control panel: run selector, current view tab, action buttons
- Main tree view: target hierarchy and detailed columns
- Bottom status bar: run info, task count, status badges, theme and connection

Speaker notes:
Users can understand the interface by thinking of it as four layers: menu, top controls, tree view, and footer summary.

---

## Slide 4. Top Panel Operations

**What users do in the top area**

- Select the current run from the ComboBox
- Check the current tab state: Main View, Trace view, or Status view
- Use primary action buttons:
  - Run All
  - Run
  - Stop
  - Skip
  - Unskip
  - Invalid

Speaker notes:
The top panel is where users choose the current run and trigger the most common execution-related actions.

---

## Slide 5. Tree View Reading Guide

**How to read the main table**

- `level`: dependency level in the flow hierarchy
- `target`: target name
- `status`: current execution state
- `tune`: available tune file suffixes
- `start time` and `end time`: execution timestamps
- `queue`, `cores`, `memory`: BSUB-related parameters

Speaker notes:
The tree view is the core working area. It combines status understanding, file access, and operation entry points into one place.

---

## Slide 6. Daily Common Actions

**Frequent actions in normal usage**

- Select one or more targets in the tree
- Right-click to open the context menu
- Execute:
  - Run selected targets
  - Stop running targets
  - Skip or unskip targets
  - Mark targets invalid
- Copy selected target names or current run path

Speaker notes:
The context menu is the fastest path for most daily target operations.

---

## Slide 7. File And Debug Access

**Quick access to related files**

- Open `log` file for debugging target output
- Open `cmd` file to inspect flow command details
- Open `csh` file to inspect target shell wrapper
- Open tune files directly from the Tune column or context menu
- Open terminal in the current run directory

Speaker notes:
This reduces the need to manually navigate directories in terminal during debug.

---

## Slide 8. Search And Filter

**Ways to narrow down what you see**

- Use target search to find matching targets quickly
- Double-click status badges in the footer to filter by one status
- Use Trace Up to see upstream dependencies
- Use Trace Down to see downstream dependencies
- Close the current filtered tab to return to Main View

Speaker notes:
The tool supports both name-based filtering and relationship-based filtering.

---

## Slide 9. Status Understanding

**Supported target status types**

- `finish`: completed successfully
- `running`: currently running
- `failed`: execution failed
- `skip`: intentionally skipped
- `scheduled`: already scheduled
- `pending`: waiting or not started yet

Speaker notes:
Status is shown both in the tree rows and in the footer badges, making it easier to scan at two levels.

---

## Slide 10. Tune And Params Workflow

**Configuration-related operations**

- Open tune files for selected targets
- Create tune files based on tunesource entries in target cmd files
- Copy tune files to other runs
- Open and edit `user.params`
- View `tile.params`
- Generate params to flow from the params editor

Speaker notes:
This area is especially useful when users need to adjust target behavior instead of only observing status.

---

## Slide 11. Status Overview Across Runs

**Run-level monitoring**

- Use `Status -> Show All Status` from the menu
- View all run directories in one summary list
- Check latest target, latest status, and timestamp for each run
- Double-click a row to copy the run name

Speaker notes:
This view is useful when users want to compare multiple runs or quickly locate a run with recent activity.

---

## Slide 12. Useful Shortcuts And Interaction Tips

**Efficiency tips**

- `Ctrl+U`: Trace Up
- `Ctrl+D`: Trace Down
- `Ctrl+P`: Open user params
- `Ctrl+Shift+P`: Open tile params
- Double-click tab label: expand or collapse all
- Double-click tree header target area: open embedded search
- Multi-select with `Ctrl+Click` or `Shift+Click`

Speaker notes:
These interactions help advanced users operate faster without relying only on mouse navigation.

---

## Slide 13. Typical User Flow

**Example daily usage flow**

- Select a run
- Scan target status in the main tree
- Filter by status or trace dependencies if needed
- Open related log, cmd, csh, or tune files
- Edit params or BSUB values when adjustment is required
- Execute Run, Stop, Skip, or Unskip actions

Speaker notes:
This slide summarizes how the tool is intended to be used in a real working session.

---

## Slide 14. Summary

**Key message**

- New-GUI is designed to make target monitoring and operation faster and clearer
- It combines visibility, file access, filtering, tracing, and execution controls
- The current version already supports the main daily tasks around run and target management

Thank you.
