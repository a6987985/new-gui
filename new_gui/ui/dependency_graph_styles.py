"""Shared stylesheet builders for the dependency graph dialog."""


def build_dependency_graph_view_style() -> str:
    """Return the graphics-view stylesheet for the dependency graph dialog."""
    return """
        QGraphicsView {
            background-color: #fafafa;
            border: 1px solid #cccccc;
            border-radius: 8px;
        }
    """


def build_dependency_graph_toolbar_button_style() -> str:
    """Return the toolbar button stylesheet for the dependency graph dialog."""
    return """
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 6px;
            padding: 6px 16px;
            font-weight: 600;
            color: #333333;
        }
        QPushButton:hover {
            background-color: #e6f7ff;
            border: 1px solid #4A90D9;
        }
        QPushButton:pressed {
            background-color: #cce5ff;
        }
    """


def build_dependency_graph_depth_combo_style() -> str:
    """Return the depth-combo stylesheet for the dependency graph dialog."""
    return """
        QComboBox {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 6px;
            padding: 4px 10px;
            color: #333333;
            min-width: 72px;
        }
        QComboBox::drop-down {
            border: none;
        }
    """


def build_dependency_graph_search_input_style() -> str:
    """Return the search-input stylesheet for the dependency graph dialog."""
    return """
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 6px;
            padding: 6px 10px;
            color: #333333;
        }
        QLineEdit:focus {
            border: 1px solid #4A90D9;
        }
    """


def build_dependency_graph_heading_label_style() -> str:
    """Return the strong heading label style for the dependency graph dialog."""
    return "font-weight: bold; color: #333;"


def build_dependency_graph_toolbar_label_style() -> str:
    """Return the toolbar label style for the dependency graph dialog."""
    return "color: #555555; font-weight: 600;"


def build_dependency_graph_meta_label_style() -> str:
    """Return the muted metadata label style for the dependency graph dialog."""
    return "color: #666; font-size: 11px;"


def build_dependency_graph_legend_item_style(background_color: str, text_color: str) -> str:
    """Return the legend badge style for one dependency graph status entry."""
    return (
        f"background-color: {background_color}; "
        f"color: {text_color}; border: 1px solid #999; border-radius: 3px; padding: 2px 6px;"
    )
