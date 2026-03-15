"""Shared stylesheet builders for reusable widget styling."""


def build_default_top_panel_style(background: str) -> str:
    """Return the default top-panel stylesheet."""
    return f"""
        #topPanel {{
            background: {background};
            border-radius: 0px;
        }}
    """


def build_xmeta_top_panel_style(bg_color: str) -> str:
    """Return the XMETA background override for the top panel."""
    return f"#topPanel {{ background-color: {bg_color}; border: none; }}"


def build_default_menu_bar_style() -> str:
    """Return the default menu-bar stylesheet."""
    return """
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #e0e0e0;
            padding: 2px 8px;
            font-size: 13px;
            font-weight: bold;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 14px;
            border-radius: 4px;
            color: #333333;
        }
        QMenuBar::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        QMenuBar::item:pressed {
            background-color: #bbdefb;
        }
        QMenu {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 4px 0px;
        }
        QMenu::item {
            padding: 8px 24px;
            color: #333333;
        }
        QMenu::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        QMenu::separator {
            height: 1px;
            background: #e0e0e0;
            margin: 4px 12px;
        }
    """


def build_xmeta_menu_bar_style(bg_color: str) -> str:
    """Return the XMETA background override for the menu bar."""
    return f"""
        QMenuBar {{
            background-color: {bg_color};
            border: none;
            padding: 4px 8px;
            font-size: 13px;
            font-weight: bold;
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 14px;
            border-radius: 4px;
            color: #333333;
        }}
        QMenuBar::item:selected {{
            background-color: #e3f2fd;
            color: #1976d2;
        }}
        QMenuBar::item:pressed {{
            background-color: #bbdefb;
        }}
        QMenu {{
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 4px 0px;
        }}
        QMenu::item {{
            padding: 8px 24px;
            color: #333333;
        }}
        QMenu::item:selected {{
            background-color: #e3f2fd;
            color: #1976d2;
        }}
        QMenu::separator {{
            height: 1px;
            background: #e0e0e0;
            margin: 4px 12px;
        }}
    """


def build_tab_bar_style(bg_color: str, border_rule: str) -> str:
    """Return the tab-bar stylesheet."""
    return f"""
        #tabBar {{
            background-color: {bg_color};
            {border_rule}
        }}
    """


def build_tab_widget_style(bg_color: str, border_rule: str, border_bottom_rule: str) -> str:
    """Return the tab-widget stylesheet."""
    return f"""
        #tabWidget {{
            background-color: {bg_color};
            {border_rule}
            {border_bottom_rule}
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }}
    """


def build_default_tree_style() -> str:
    """Return the default tree-view stylesheet."""
    return """
        QTreeView {
            background: rgba(255, 255, 255, 0.96);
            border: none;
            font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
            font-size: 10pt;
            border-radius: 10px;
            padding: 6px 4px 4px 4px;
        }
        QTreeView::item {
            height: 17px;
            padding: 5px 6px;
            border: none;
        }
        QTreeView:focus {
            outline: none;
        }
        QHeaderView {
            background: transparent;
            border: none;
        }
        QHeaderView::section {
            background: transparent;
            padding: 0px;
            border: none;
            font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
            font-size: 10pt;
            font-weight: 600;
            color: #475569;
        }
        QTreeView::item:hover {
            background: transparent;
        }
        QTreeView::item:selected {
            background: transparent;
            color: #000000 !important;
            outline: none;
        }
        QTreeView::branch {
            background: transparent;
            border: none;
        }
        QTreeView::branch:has-siblings:!adjoins-item {
            background: transparent;
        }
        QTreeView::branch:has-siblings:adjoins-item {
            background: transparent;
        }
        QTreeView::branch:!has-children:!has-siblings:adjoins-item {
            background: transparent;
        }
        QTreeView::branch:has-children:!has-siblings:closed {
            background: transparent;
            image: none;
        }
        QTreeView::branch:has-children:!has-siblings:open {
            background: transparent;
            image: none;
        }
        QTreeView::branch:has-children:has-siblings:closed {
            image: none;
        }
        QTreeView::branch:has-children:has-siblings:open {
            image: none;
        }
        QTreeView::branch:closed:has-children {
            border-image: none;
        }
        QTreeView::branch:open:has-children {
            border-image: none;
        }
        QTreeView::branch:selected {
            background: #C0C0BE !important;
        }
        QTreeView::branch:has-siblings:!adjoins-item:selected {
            background: #C0C0BE !important;
        }
        QTreeView::branch:has-siblings:adjoins-item:selected {
            background: #C0C0BE !important;
        }
        QTreeView::branch:!has-children:!has-siblings:adjoins-item:selected {
            background: #C0C0BE !important;
        }
        QTreeView::branch:has-children:!has-siblings:closed:selected,
        QTreeView::branch:has-children:!has-siblings:open:selected {
            background: #C0C0BE !important;
        }
        QTreeView::branch:hover {
            background: rgba(230,240,255,0.6) !important;
        }
    """


def build_xmeta_tree_style(text_color: str) -> str:
    """Return the XMETA background override for the tree view."""
    return f"""
        QTreeView {{
            background: rgba(255, 255, 255, 0.9);
            border: none;
            font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
            font-size: 10pt;
            border-radius: 10px;
            padding: 6px 4px 4px 4px;
        }}
        QTreeView::item {{
            height: 17px;
            padding: 5px 6px;
            border: none;
        }}
        QTreeView:focus {{
            outline: none;
        }}
        QHeaderView {{
            background: transparent;
            border: none;
        }}
        QHeaderView::section {{
            background: transparent;
            padding: 0px;
            border: none;
            font-family: "Segoe UI", "Helvetica Neue", "Arial", sans-serif;
            font-size: 10pt;
            font-weight: 600;
            color: {text_color};
        }}
        QTreeView::item:hover {{
            background: transparent;
        }}
        QTreeView::item:selected {{
            background: transparent;
            color: #000000 !important;
            outline: none;
        }}
        QTreeView::branch {{
            background: transparent;
            border: none;
        }}
        QTreeView::branch:has-siblings:!adjoins-item {{
            background: transparent;
        }}
        QTreeView::branch:has-siblings:adjoins-item {{
            background: transparent;
        }}
        QTreeView::branch:!has-children:!has-siblings:adjoins-item {{
            background: transparent;
        }}
        QTreeView::branch:has-children:!has-siblings:closed {{
            background: transparent;
            image: none;
        }}
        QTreeView::branch:has-children:!has-siblings:open {{
            background: transparent;
            image: none;
        }}
        QTreeView::branch:has-children:has-siblings:closed {{
            image: none;
        }}
        QTreeView::branch:has-children:has-siblings:open {{
            image: none;
        }}
        QTreeView::branch:closed:has-children {{
            border-image: none;
        }}
        QTreeView::branch:open:has-children {{
            border-image: none;
        }}
        QTreeView::branch:selected {{
            background: #C0C0BE !important;
        }}
        QTreeView::branch:has-siblings:!adjoins-item:selected {{
            background: #C0C0BE !important;
        }}
        QTreeView::branch:has-siblings:adjoins-item:selected {{
            background: #C0C0BE !important;
        }}
        QTreeView::branch:!has-children:!has-siblings:adjoins-item:selected {{
            background: #C0C0BE !important;
        }}
        QTreeView::branch:has-children:!has-siblings:closed:selected,
        QTreeView::branch:has-children:!has-siblings:open:selected {{
            background: #C0C0BE !important;
        }}
        QTreeView::branch:hover {{
            background: rgba(230,240,255,0.6) !important;
        }}
    """


def build_xmeta_status_bar_style(bg_color: str, text_color: str) -> str:
    """Return the XMETA background override for the status bar."""
    return f"""
        StatusBar {{
            background-color: {bg_color};
            border-top: none;
        }}
        QLabel {{
            color: {text_color};
            font-size: 12px;
        }}
    """
