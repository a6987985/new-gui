import os
import logging
import re

# ========== Logging Setup ==========
DEFAULT_LOG_LEVEL_NAME = os.environ.get("NEW_GUI_LOG_LEVEL", "WARNING").upper()
DEFAULT_LOG_LEVEL = getattr(logging, DEFAULT_LOG_LEVEL_NAME, logging.WARNING)
logging.basicConfig(
    level=DEFAULT_LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ========== Pre-compiled Regex Patterns ==========
RE_LEVEL_LINE = re.compile(r'^set\s+LEVEL_(\d+)\s*=\s*"([^"]*)"')
RE_ACTIVE_TARGETS = re.compile(r'set\s*ACTIVE_TARGETS\s*=\s*"([^"]*)"')
RE_TARGET_LEVEL = re.compile(r'set\s*(TARGET_LEVEL_\w+)\s*=\s*(.*)')
RE_QUOTED_STRING = re.compile(r"^['\"](.*)['\"]\s*$")
RE_DEPENDENCY_OUT = re.compile(r'set\s+DEPENDENCY_OUT_(\w+)\s*=\s*"([^"]*)"')
RE_ALL_RELATED = re.compile(r'set\s+ALL_RELATED_(\w+)\s*=\s*"([^"]*)"')
RE_PARAM_LINE = re.compile(r'^\s*(\w+)\s*=\s*(.+?)\s*$')

# ========== Status Configuration Constant ==========
STATUS_CONFIG = {
    "finish": {"color": "#98FB98", "icon": "✓", "animation": None, "text_color": "#1a5f1a"},
    "skip": {"color": "#FFDAB9", "icon": "○", "animation": None, "text_color": "#8b6914"},
    "running": {"color": "#FFFF00", "icon": "▶", "animation": "pulse", "text_color": "#333333"},
    "failed": {"color": "#FF9999", "icon": "✗", "animation": "shake", "text_color": "#8b0000"},
    "scheduled": {"color": "#4A90D9", "icon": "◷", "animation": None, "text_color": "#ffffff"},
    "pending": {"color": "#FFA500", "icon": "◇", "animation": None, "text_color": "#333333"},
    "": {"color": "#88D0EC", "icon": "", "animation": None, "text_color": "#1a4f6f"}
}

STATUS_COLORS = {k: v["color"] for k, v in STATUS_CONFIG.items()}

# ========== Theme Configuration ==========
THEMES = {
    "light": {
        "name": "Light",
        "window_bg": "#f5f5f5",
        "panel_bg": "#f8f9fa",
        "tree_bg": "rgba(255, 255, 255, 0.95)",
        "text_color": "#333333",
        "accent_color": "#1976d2",
        "border_color": "#e0e0e0",
        "hover_bg": "#e3f2fd",
        "selection_bg": "#bbdefb",
        "menu_bg": "#ffffff",
        "menu_hover": "#e3f2fd",
        "status_bar_bg": "#ffffff"
    },
    "dark": {
        "name": "Dark",
        "window_bg": "#1a1a2e",
        "panel_bg": "#2d3436",
        "tree_bg": "rgba(30, 30, 40, 0.95)",
        "text_color": "#e0e0e0",
        "accent_color": "#64b5f6",
        "border_color": "#444444",
        "hover_bg": "rgba(80, 80, 100, 0.5)",
        "selection_bg": "#3d5a80",
        "menu_bg": "#2d2d2d",
        "menu_hover": "#3d5a80",
        "status_bar_bg": "#252525"
    },
    "high_contrast": {
        "name": "High Contrast",
        "window_bg": "#ffffff",
        "panel_bg": "#000000",
        "tree_bg": "#ffffff",
        "text_color": "#000000",
        "accent_color": "#0000ff",
        "border_color": "#000000",
        "hover_bg": "#ffff00",
        "selection_bg": "#0000ff",
        "menu_bg": "#ffffff",
        "menu_hover": "#0000ff",
        "status_bar_bg": "#e0e0e0"
    }
}

# ========== Keyboard Shortcuts Configuration ==========
SHORTCUTS = {
    "search": {"key": "Ctrl+F", "description": "Focus search field"},
    "refresh": {"key": "Ctrl+R", "description": "Refresh current view"},
    "expand_all": {"key": "Ctrl+E", "description": "Expand all items"},
    "collapse_all": {"key": "Ctrl+W", "description": "Collapse all items"},
    "toggle_theme": {"key": "Ctrl+T", "description": "Toggle dark/light theme"},
    "show_graph": {"key": "Ctrl+G", "description": "Show dependency graph"},
    "copy_target": {"key": "Ctrl+C", "description": "Copy selected target name"},
    "run_selected": {"key": "Ctrl+Enter", "description": "Run selected targets"},
    "trace_up": {"key": "Ctrl+U", "description": "Trace upstream dependencies"},
    "trace_down": {"key": "Ctrl+D", "description": "Trace downstream dependencies"},
    "user_params": {"key": "Ctrl+P", "description": "Open user.params editor"},
    "tile_params": {"key": "Ctrl+Shift+P", "description": "View tile.params"}
}

# ========== Notification Types ==========
NOTIFICATION_TYPES = {
    "info": {"color": "#4A90D9", "icon": "ℹ", "duration": 3000},
    "success": {"color": "#28a745", "icon": "✓", "duration": 3000},
    "warning": {"color": "#ffc107", "icon": "⚠", "duration": 5000},
    "error": {"color": "#dc3545", "icon": "✗", "duration": 7000}
}

# ========== Timing Constants ==========
DEBOUNCE_DELAY_MS = 300
BACKUP_TIMER_INTERVAL_MS = 10000
ANIMATION_DURATION_MS = 200
FADE_IN_DURATION_MS = 600

# ========== UI Dimension Constants ==========
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 960
MAX_NOTIFICATIONS = 5
NOTIFICATION_SPACING = 10
NOTIFICATION_MARGIN_BOTTOM = 80
NOTIFICATION_MARGIN_RIGHT = 20

# ========== Styles ==========
STYLES = {
    'button_primary': """
        QPushButton {
            background-color: #1976d2;
            border: none;
            border-radius: 6px;
            padding: 6px 14px;
            font-weight: 500;
            font-size: 12px;
            color: #ffffff;
        }
        QPushButton:hover { background-color: #1565c0; }
        QPushButton:pressed { background-color: #0d47a1; }
    """,
    'button_default': """
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            padding: 6px 14px;
            font-weight: 500;
            font-size: 12px;
            color: #333333;
        }
        QPushButton:hover { background-color: #f5f5f5; border: 1px solid #1976d2; color: #1976d2; }
        QPushButton:pressed { background-color: #e3f2fd; border: 1px solid #1976d2; }
    """,
    'button_warning': """
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #ffcdd2;
            border-radius: 6px;
            padding: 6px 14px;
            font-weight: 500;
            font-size: 12px;
            color: #c62828;
        }
        QPushButton:hover { background-color: #ffebee; border: 1px solid #ef5350; }
        QPushButton:pressed { background-color: #ffcdd2; }
    """,
    'menu': """
        QMenu {
            background-color: white;
            border: 1px solid #cccccc;
            border-radius: 6px;
            padding: 4px 0px;
        }
        QMenu::item { padding: 6px 30px 6px 10px; border-radius: 0px; }
        QMenu::item:selected { background-color: #e6f7ff; }
        QMenu::separator { height: 1px; background: #e0e0e0; margin: 4px 10px; }
    """,
    'button_close': """
        QPushButton {
            border: none;
            border-radius: 10px;
            color: #999999;
            font-weight: bold;
            background: transparent;
            font-size: 16px;
        }
        QPushButton:hover { background-color: #ef5350; color: white; }
    """,
}
