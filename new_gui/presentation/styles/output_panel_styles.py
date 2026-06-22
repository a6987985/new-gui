"""Shared stylesheet builders for the bottom output area widgets."""


def _build_panel_button_rules(selector: str) -> str:
    """Return shared output-panel button rules for a specific selector."""
    return f"""
        {selector} {{
            background-color: #fafcfd;
            border: 1px solid #d9e1e8;
            border-radius: 6px;
            color: #5c6d7e;
            font-weight: 600;
            padding: 3px 10px;
        }}
        {selector}:hover {{
            background-color: #eef3f7;
            border: 1px solid #c9d5e0;
        }}
        {selector}:pressed {{
            background-color: #e6edf4;
            border: 1px solid #bccbda;
        }}
    """


def build_session_log_style() -> str:
    """Return the widget stylesheet for the session log area."""
    return (
        """
        QWidget#sessionLogWidget {
            background-color: #f6f9fb;
        }
        QLabel#sessionLogTitle {
            color: #526476;
            font-weight: 600;
            font-size: 12px;
        }
        QTextBrowser#sessionLogView {
            background-color: #fcfdfe;
            border: 1px solid #dbe3eb;
            border-radius: 6px;
            color: #314154;
            padding: 5px;
        }
        """
        + _build_panel_button_rules("QPushButton#sessionLogButton")
    )


def build_session_log_document_style() -> str:
    """Return the HTML document stylesheet used inside the session log view."""
    return """
        body {
            color: #314154;
            font-size: 12px;
        }
        .entry { margin-bottom: 10px; }
        .meta { margin-bottom: 4px; }
        .timestamp { color: #7b8794; }
        .source { color: #6e8cac; }
        .message { color: #2f3d4c; }
        .command-label, .details-label {
            color: #6885a2;
            font-weight: 600;
            margin-top: 4px;
        }
        pre {
            white-space: pre-wrap;
            margin: 4px 0 0 0;
            padding: 6px 8px;
            background: #f5f8fa;
            border: 1px solid #dee5ec;
            border-radius: 5px;
            color: #314154;
            font-family: monospace;
        }
    """


def build_bottom_output_panel_style() -> str:
    """Return the root panel stylesheet for the bottom output area."""
    return """
        QWidget#bottomOutputPanel {
            background-color: #e9eff4;
        }
    """


def build_bottom_output_tab_style() -> str:
    """Return the tab widget stylesheet for the bottom output area."""
    return """
        QTabWidget {
            background-color: #e9eff4;
        }
        QTabWidget::tab-bar {
            alignment: left;
            left: 12px;
        }
        QTabWidget::pane {
            border-top: 1px solid #d6dee7;
            background-color: #f6f9fb;
            top: -1px;
        }
        QTabBar::tab {
            background: transparent;
            color: #738293;
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 5px 14px;
            margin: 8px 4px 0 0;
            font-size: 12px;
            font-weight: 600;
        }
        QTabBar::tab:hover {
            background: #e3eaf0;
            color: #556779;
        }
        QTabBar::tab:selected {
            background: #f6f9fb;
            color: #334657;
            border: 1px solid #d0d8e1;
            border-bottom-color: #f6f9fb;
            margin-bottom: -1px;
        }
        QTabBar::tab:selected:hover {
            background: #f6f9fb;
        }
    """


def build_bottom_output_corner_style() -> str:
    """Return the corner-controls stylesheet for the bottom output area."""
    return (
        _build_panel_button_rules("QPushButton#bottomOutputActionButton")
        + """
        QToolButton#terminalFollowRunButton,
        QToolButton#terminalContentFillButton {
            background-color: #fafcfd;
            border: 1px solid #d9e1e8;
            border-radius: 6px;
            padding: 0px;
        }
        QToolButton#terminalFollowRunButton:hover,
        QToolButton#terminalContentFillButton:hover {
            background-color: #eef3f7;
            border: 1px solid #c9d5e0;
        }
        QToolButton#terminalFollowRunButton:checked {
            background-color: #e7f1fb;
            border: 1px solid #5d8fcf;
        }
        QToolButton#terminalFollowRunButton:checked:hover {
            background-color: #dcebf9;
            border: 1px solid #4f83c6;
        }
        QToolButton#terminalContentFillButton:checked {
            background-color: #111827;
            border: 1px solid #111827;
        }
        QToolButton#terminalContentFillButton:checked:hover {
            background-color: #000000;
            border: 1px solid #000000;
        }
        """
    )


def build_embedded_terminal_style() -> str:
    """Return the widget stylesheet for the embedded terminal area."""
    return """
        QWidget#embeddedTerminalPanel {
            background-color: #f6f9fb;
        }
        QLabel#embeddedTerminalMessage {
            color: #526476;
            font-size: 12px;
        }
        QFrame#embeddedTerminalHost {
            background-color: #ffffff;
            border: 1px solid #dbe3eb;
            border-radius: 6px;
        }
    """



# ====================== Theme-aware variants ======================


def _color_palette(theme: dict) -> dict:
    """Map a theme dict to the colors used by the output panel."""
    panel_bg = theme.get("panel_bg", "#f6f9fb")
    menu_bg = theme.get("menu_bg", "#fafcfd")
    text_color = theme.get("text_color", "#314154")
    border_color = theme.get("border_color", "#d9e1e8")
    accent_color = theme.get("accent_color", "#5d8fcf")
    hover_bg = theme.get("hover_bg", "#eef3f7")
    muted = theme.get("muted_color") or theme.get("hint_color", "#5c6d7e")
    selection_bg = theme.get("selection_bg", "#dfeefd")
    return {
        "panel_bg": panel_bg,
        "menu_bg": menu_bg,
        "text": text_color,
        "border": border_color,
        "accent": accent_color,
        "hover": hover_bg,
        "muted": muted,
        "selection": selection_bg,
    }


def _theme_button_rules(selector: str, palette: dict) -> str:
    """Return panel-button rules using the theme palette."""
    return f"""
        {selector} {{
            background-color: {palette['menu_bg']};
            border: 1px solid {palette['border']};
            border-radius: 6px;
            color: {palette['muted']};
            font-weight: 600;
            padding: 3px 10px;
        }}
        {selector}:hover {{
            background-color: {palette['hover']};
            border: 1px solid {palette['accent']};
            color: {palette['accent']};
        }}
        {selector}:pressed {{
            background-color: {palette['selection']};
            border: 1px solid {palette['accent']};
        }}
    """


def build_session_log_style_themed(theme: dict) -> str:
    """Theme-aware variant of build_session_log_style."""
    p = _color_palette(theme)
    return f"""
        QWidget#sessionLogWidget {{
            background-color: {p['panel_bg']};
        }}
        QLabel#sessionLogTitle {{
            color: {p['text']};
            font-weight: 600;
            font-size: 12px;
        }}
        QTextBrowser#sessionLogView {{
            background-color: {p['menu_bg']};
            border: 1px solid {p['border']};
            border-radius: 6px;
            color: {p['text']};
            padding: 5px;
        }}
    """ + _theme_button_rules("QPushButton#sessionLogButton", p)


def build_session_log_document_style_themed(theme: dict) -> str:
    """Theme-aware variant of session log document HTML style."""
    p = _color_palette(theme)
    return f"""
        body {{
            color: {p['text']};
            font-size: 12px;
        }}
        .entry {{ margin-bottom: 10px; }}
        .meta {{ margin-bottom: 4px; }}
        .timestamp {{ color: {p['muted']}; }}
        .source {{ color: {p['accent']}; }}
        .message {{ color: {p['text']}; }}
        .command-label, .details-label {{
            color: {p['accent']};
            font-weight: 600;
            margin-top: 4px;
        }}
        pre {{
            white-space: pre-wrap;
            margin: 4px 0 0 0;
            padding: 6px 8px;
            background: {p['menu_bg']};
            border: 1px solid {p['border']};
            border-radius: 5px;
            color: {p['text']};
            font-family: monospace;
        }}
    """


def build_bottom_output_panel_style_themed(theme: dict) -> str:
    """Theme-aware variant of build_bottom_output_panel_style."""
    p = _color_palette(theme)
    return f"""
        QWidget#bottomOutputPanel {{
            background-color: {p['panel_bg']};
        }}
    """


def build_bottom_output_tab_style_themed(theme: dict) -> str:
    """Theme-aware variant of build_bottom_output_tab_style."""
    p = _color_palette(theme)
    return f"""
        QTabWidget {{
            background-color: {p['panel_bg']};
        }}
        QTabWidget::tab-bar {{
            alignment: left;
            left: 12px;
        }}
        QTabWidget::pane {{
            border-top: 1px solid {p['border']};
            background-color: {p['panel_bg']};
            top: -1px;
        }}
        QTabBar::tab {{
            background: transparent;
            color: {p['muted']};
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 5px 14px;
            margin: 8px 4px 0 0;
            font-size: 12px;
            font-weight: 600;
        }}
        QTabBar::tab:hover {{
            background: {p['hover']};
            color: {p['text']};
        }}
        QTabBar::tab:selected {{
            background: {p['panel_bg']};
            color: {p['accent']};
            border: 1px solid {p['border']};
            border-bottom-color: {p['panel_bg']};
            margin-bottom: -1px;
        }}
        QTabBar::tab:selected:hover {{
            background: {p['panel_bg']};
        }}
    """


def build_bottom_output_corner_style_themed(theme: dict) -> str:
    """Theme-aware variant of build_bottom_output_corner_style."""
    p = _color_palette(theme)
    return _theme_button_rules("QPushButton#bottomOutputActionButton", p) + f"""
        QToolButton#terminalFollowRunButton,
        QToolButton#terminalContentFillButton {{
            background-color: {p['menu_bg']};
            border: 1px solid {p['border']};
            border-radius: 6px;
            padding: 0px;
        }}
        QToolButton#terminalFollowRunButton:hover,
        QToolButton#terminalContentFillButton:hover {{
            background-color: {p['hover']};
            border: 1px solid {p['accent']};
        }}
        QToolButton#terminalFollowRunButton:checked {{
            background-color: {p['selection']};
            border: 1px solid {p['accent']};
        }}
        QToolButton#terminalFollowRunButton:checked:hover {{
            background-color: {p['hover']};
            border: 1px solid {p['accent']};
        }}
        QToolButton#terminalContentFillButton:checked {{
            background-color: #111827;
            border: 1px solid #111827;
        }}
        QToolButton#terminalContentFillButton:checked:hover {{
            background-color: #000000;
            border: 1px solid #000000;
        }}
    """


def build_embedded_terminal_style_themed(theme: dict) -> str:
    """Theme-aware variant of build_embedded_terminal_style."""
    p = _color_palette(theme)
    return f"""
        QWidget#embeddedTerminalPanel {{
            background-color: {p['panel_bg']};
        }}
        QLabel#embeddedTerminalMessage {{
            color: {p['text']};
            font-size: 12px;
        }}
        QFrame#embeddedTerminalHost {{
            background-color: {p['menu_bg']};
            border: 1px solid {p['border']};
            border-radius: 6px;
        }}
    """
