"""Style helpers for presentation layer."""



def _current_theme_dict():
    """Return the current theme dict from ThemeManager singleton."""
    try:
        from new_gui.presentation.theme.theme_runtime import ThemeManager
        return ThemeManager().get_theme()
    except Exception:
        return {}

def current_theme_dict():
    """Return the current theme dict from the global ThemeManager singleton."""
    from new_gui.presentation.theme.theme_runtime import ThemeManager
    return ThemeManager().get_theme()
