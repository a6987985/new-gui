"""Helpers for restoring filtered main-tree views after a rebuild."""


def build_restore_plan(tab_label_text: str, header_filter_text: str, scroll_value: int) -> dict:
    """Build a restore plan for the current main-tree presentation mode."""
    tab_text = (tab_label_text or "").strip()
    search_text = header_filter_text or ""

    if tab_text.startswith("Trace"):
        parts = tab_text.split(": ", 1)
        if len(parts) == 2:
            direction_str, target_name = parts
            return {
                "mode": "trace",
                "target_name": target_name,
                "inout": "in" if "Up" in direction_str else "out",
                "scroll": scroll_value,
            }
        return {"mode": "trace", "scroll": scroll_value}

    if tab_text.startswith("Status: "):
        status = tab_text.replace("Status: ", "", 1).strip().lower()
        if status:
            return {
                "mode": "status",
                "status": status,
                "scroll": scroll_value,
            }

    if search_text:
        return {
            "mode": "search",
            "search_text": search_text,
            "scroll": scroll_value,
        }

    return {"mode": "main", "scroll": scroll_value}


def apply_restore_plan(
    plan: dict,
    get_retrace_target,
    filter_tree_by_targets,
    apply_status_filter,
    filter_tree,
    set_scroll_value,
    show_status_close_button=None,
) -> str:
    """Replay the filtered view described by a restore plan."""
    mode = (plan or {}).get("mode", "main")

    if mode == "trace":
        target_name = plan.get("target_name", "")
        inout = plan.get("inout")
        if target_name and inout:
            related_targets = list(get_retrace_target(target_name, inout) or [])
            if target_name not in related_targets:
                if inout == "in":
                    related_targets.append(target_name)
                else:
                    related_targets.insert(0, target_name)
            filter_tree_by_targets(set(related_targets))
    elif mode == "status":
        status = plan.get("status", "")
        if status:
            apply_status_filter(status, update_tab=False)
            if show_status_close_button is not None:
                show_status_close_button()
    elif mode == "search":
        search_text = plan.get("search_text", "")
        if search_text:
            filter_tree(search_text)

    set_scroll_value(plan.get("scroll", 0))
    return mode
