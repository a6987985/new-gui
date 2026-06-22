from pathlib import Path
import ast
import importlib.util
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT


class RepoLayoutTests(unittest.TestCase):
    def test_package_main_exists(self) -> None:
        self.assertTrue((PACKAGE_ROOT / "main.py").is_file())

    def test_root_bundle_tool_exists(self) -> None:
        self.assertTrue((REPO_ROOT / "tools" / "export_patch_bundle.py").is_file())

    def test_new_gui_main_is_importable(self) -> None:
        spec = importlib.util.find_spec("new_gui.main")
        self.assertIsNotNone(spec)

    def test_content_tab_controller_does_not_depend_on_view_builder_internals(self) -> None:
        source = (PACKAGE_ROOT / "presentation" / "presenters" / "content_tab_controller.py").read_text()
        self.assertNotIn("top_panel_builder", source)

    def test_infrastructure_repositories_do_not_import_model_services(self) -> None:
        repository_dir = PACKAGE_ROOT / "infrastructure" / "repositories"
        violations = []
        for path in repository_dir.rglob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("new_gui.model"):
                    violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}:{node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("new_gui.model"):
                            violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}:{alias.name}")
        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
