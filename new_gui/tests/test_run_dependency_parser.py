import os
import tempfile
import unittest

from new_gui.infrastructure.repositories.run_dependency_parser import parse_collapsible_target_groups
from new_gui.infrastructure.repositories.run_dependency_query import (
    build_direct_downstream_map,
    build_trace_targets_from_content,
    get_retrace_targets,
)


class RunDependencyParserTests(unittest.TestCase):
    def test_collapsible_groups_parse_instances_list_after_level_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_name = "sample_run"
            run_dir = os.path.join(tmp_dir, run_name)
            os.makedirs(run_dir, exist_ok=True)
            dependency_file = os.path.join(run_dir, ".target_dependency.csh")
            with open(dependency_file, "w", encoding="utf-8") as handle:
                handle.write('set LEVEL_1 = "alpha beta gamma"\n')
                handle.write('set INSTANCES_LIST_TIMING_Generic = "alpha beta gamma"\n')

            groups = parse_collapsible_target_groups(tmp_dir, run_name)

        self.assertEqual({"Generic": ["alpha", "beta", "gamma"]}, groups)

    def test_retrace_targets_supports_in_out_direction_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dependency_file = os.path.join(tmp_dir, ".target_dependency.csh")
            with open(dependency_file, "w", encoding="utf-8") as handle:
                handle.write('set ALL_RELATED_target_b = "target_a target_b" "target_c"\n')

            upstream_targets = get_retrace_targets(tmp_dir, "target_b", "in")
            downstream_targets = get_retrace_targets(tmp_dir, "target_b", "out")

        self.assertEqual(["target_a", "target_b"], upstream_targets)
        self.assertEqual(["target_c"], downstream_targets)

    def test_direct_downstream_map_uses_dependency_out_payload(self) -> None:
        content = 'set DEPENDENCY_OUT_target_a = "target_b target_c"\n'

        downstream_map = build_direct_downstream_map(content, ["target_a", "target_b"])

        self.assertEqual(["target_b", "target_c"], downstream_map["target_a"])
        self.assertEqual([], downstream_map["target_b"])

    def test_retrace_targets_falls_back_to_dependency_out_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dependency_file = os.path.join(tmp_dir, ".target_dependency.csh")
            with open(dependency_file, "w", encoding="utf-8") as handle:
                handle.write('set DEPENDENCY_OUT_target_a = "target_b"\n')
                handle.write('set DEPENDENCY_OUT_target_b = "target_c"\n')

            upstream_targets = get_retrace_targets(tmp_dir, "target_c", "in")
            downstream_targets = get_retrace_targets(tmp_dir, "target_a", "out")

        self.assertEqual(["target_a", "target_b"], upstream_targets)
        self.assertEqual(["target_b", "target_c"], downstream_targets)

    def test_trace_targets_falls_back_to_dependency_out_edges(self) -> None:
        content = (
            'set DEPENDENCY_OUT_target_a = "target_b"\n'
            'set DEPENDENCY_OUT_target_b = "target_c"\n'
        )

        trace_targets = build_trace_targets_from_content(
            content,
            ["target_a", "target_b", "target_c"],
        )

        self.assertEqual(["target_a", "target_b"], trace_targets["upstream"]["target_c"])
        self.assertEqual(["target_b", "target_c"], trace_targets["downstream"]["target_a"])


if __name__ == "__main__":
    unittest.main()
