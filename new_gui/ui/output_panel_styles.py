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


def build_embedded_terminal_style() -> str:
    """Return the widget stylesheet for the embedded terminal area."""
    return (
        """
        QWidget#embeddedTerminalPanel {
            background-color: #f6f9fb;
            border-top: 1px solid #d6dee7;
        }
        QLabel#embeddedTerminalTitle {
            color: #526476;
            font-weight: 600;
            font-size: 12px;
        }
        QLabel#embeddedTerminalPath {
            color: #7b8794;
            font-size: 11px;
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
        + _build_panel_button_rules("QPushButton#embeddedTerminalButton")
    )
