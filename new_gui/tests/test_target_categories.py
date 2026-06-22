import os
import tempfile
import unittest
from unittest.mock import patch

from new_gui.infrastructure.repositories import target_categories
from new_gui.main import MainWindow


class TargetCategoryBootstrapTests(unittest.TestCase):
    def test_ensure_shared_target_stage_file_is_non_invasive_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            expected_gui_dir = target_categories.resolve_shared_target_stage_dir(tmp_dir)

            target_file, created_gui_dir, copied_target_file, error_message = (
                target_categories.ensure_shared_target_stage_file(
                    execution_dir=tmp_dir,
                    source_file=os.path.join(tmp_dir, "missing_target_stage.list"),
                )
            )

            self.assertEqual(os.path.join(expected_gui_dir, "target_stage.list"), target_file)
            self.assertFalse(created_gui_dir)
            self.assertFalse(copied_target_file)
            self.assertEqual("", error_message)
            self.assertFalse(os.path.exists(expected_gui_dir))

    def test_ensure_shared_target_stage_file_creates_gui_dir_and_copies_source_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            execution_dir = os.path.join(tmp_dir, "workspace", "new_gui")
            os.makedirs(execution_dir, exist_ok=True)
            source_file = os.path.join(tmp_dir, "source_target_stage.list")
            with open(source_file, "w", encoding="utf-8") as handle:
                handle.write('stage_a "alpha beta"\\n')

            target_file, created_gui_dir, copied_target_file, error_message = (
                target_categories.ensure_shared_target_stage_file(
                    execution_dir=execution_dir,
                    source_file=source_file,
                    create_gui_dir=True,
                    copy_target_file=True,
                )
            )

            self.assertTrue(os.path.isdir(os.path.dirname(target_file)))
            self.assertTrue(copied_target_file)
            self.assertEqual("", error_message)
            self.assertTrue(os.path.isfile(target_file))
            with open(target_file, "r", encoding="utf-8") as handle:
                self.assertEqual('stage_a "alpha beta"\\n', handle.read())

    def test_main_window_bootstrap_requests_gui_dir_creation_and_copy(self) -> None:
        with patch("new_gui.main.target_categories.ensure_shared_target_stage_file") as ensure_mock:
            ensure_mock.return_value = ("/tmp/target_stage.list", False, False, "")

            MainWindow._ensure_shared_target_stage_file(object())

            ensure_mock.assert_called_once_with(
                create_gui_dir=True,
                copy_target_file=True,
            )


if __name__ == "__main__":
    unittest.main()
