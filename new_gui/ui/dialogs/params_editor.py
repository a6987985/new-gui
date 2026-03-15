import os
import re
import shlex
import shutil
import subprocess
import time

from PyQt5.QtCore import QModelIndex, Qt, QAbstractTableModel, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QShortcut,
    QTableView,
    QVBoxLayout,
    QLabel,
)

from new_gui.config.settings import RE_PARAM_LINE, logger


class ParamsTableModel(QAbstractTableModel):
    """High-performance table model for params data using virtualization"""

    def __init__(self, params_data=None, parent=None):
        super().__init__(parent)
        self._data = []  # List of (param_name, value) tuples
        self._filtered_data = []  # Filtered view
        self._filter_text = ""
        if params_data:
            self.set_data(params_data)

    def set_data(self, params_data):
        """Set data from dict and sort"""
        self.beginResetModel()
        self._data = sorted(params_data.items())
        self._apply_filter()
        self.endResetModel()

    def set_filter(self, filter_text):
        """Apply filter to data"""
        self.beginResetModel()
        self._filter_text = filter_text.lower()
        self._apply_filter()
        self.endResetModel()

    def _apply_filter(self):
        """Apply current filter to data"""
        if not self._filter_text:
            self._filtered_data = self._data[:]
        else:
            self._filtered_data = [
                (name, value) for name, value in self._data
                if self._filter_text in name.lower()
            ]

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._filtered_data)

    def columnCount(self, parent=QModelIndex()):
        return 2  # Parameter, Value

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._filtered_data):
            return None

        param_name, value = self._filtered_data[index.row()]

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if index.column() == 0:
                return param_name
            elif index.column() == 1:
                return str(value)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ["Parameter", "Value"][section]
        return None

    def get_param(self, row):
        """Get param name and value at row"""
        if 0 <= row < len(self._filtered_data):
            return self._filtered_data[row]
        return None, None

    def total_count(self):
        """Get total (unfiltered) count"""
        return len(self._data)

    def filtered_count(self):
        """Get filtered count"""
        return len(self._filtered_data)


# ========== Params Editor Dialog (Optimized) ==========
class ParamsEditorDialog(QDialog):
    """Dialog for editing user.params and viewing tile.params - optimized for large files"""

    def __init__(self, params_file, params_type="user", parent=None):
        """
        Args:
            params_file: Path to the params file
            params_type: "user" for editable, "tile" for read-only
            parent: Parent widget
        """
        super().__init__(parent)
        self.params_file = params_file
        self.params_type = params_type
        self.is_readonly = (params_type == "tile")
        self.params_data = {}  # {param_name: value}
        self.modified = False
        self._search_debounce_timer = QTimer()
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.timeout.connect(self._do_filter)

        # Extract run directory from params file path
        self.run_dir = os.path.dirname(params_file)

        self._setup_ui()
        self._load_params()

    def _setup_ui(self):
        """Setup the dialog UI"""
        title = f"{'📝' if self.params_type == 'user' else '📋'} {self.params_type.title()} Params Editor"
        if self.is_readonly:
            title += " (Read Only)"
        self.setWindowTitle(title)
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header with file path
        header_layout = QHBoxLayout()
        file_label = QLabel(f"File: {self.params_file}")
        file_label.setStyleSheet("color: #666; font-size: 11px;")
        file_label.setWordWrap(True)
        header_layout.addWidget(file_label)
        header_layout.addStretch()

        # Search and buttons
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search parameters... (type and wait)")
        self.search_input.textChanged.connect(self._debounced_filter)
        search_layout.addWidget(self.search_input)

        # Clear search button
        clear_btn = QPushButton("✕")
        clear_btn.setFixedSize(28, 28)
        clear_btn.setToolTip("Clear search")
        clear_btn.clicked.connect(self._clear_search)
        search_layout.addWidget(clear_btn)

        if not self.is_readonly:
            add_btn = QPushButton("➕ Add")
            add_btn.setFixedWidth(80)
            add_btn.clicked.connect(self._add_param)
            search_layout.addWidget(add_btn)

        layout.addLayout(header_layout)
        layout.addLayout(search_layout)

        # Params table - use QTableView with custom model for performance
        self.table = QTableView()
        self._model = ParamsTableModel()
        self.table.setModel(self._model)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(False)  # Disable for better performance
        self.table.verticalHeader().setVisible(False)

        # Double-click to edit/copy
        self.table.doubleClicked.connect(self._on_double_click)

        # Context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

        # Edit panel (only for user params)
        if not self.is_readonly:
            edit_group = QGroupBox("Edit Parameter")
            edit_layout = QHBoxLayout(edit_group)

            edit_layout.addWidget(QLabel("Parameter:"))
            self.param_input = QLineEdit()
            self.param_input.setPlaceholderText("PARAM_NAME")
            self.param_input.setFixedWidth(200)
            edit_layout.addWidget(self.param_input)

            edit_layout.addWidget(QLabel("Value:"))
            self.value_input = QLineEdit()
            self.value_input.setPlaceholderText("value")
            edit_layout.addWidget(self.value_input)

            update_btn = QPushButton("Update")
            update_btn.clicked.connect(self._update_param)
            edit_layout.addWidget(update_btn)

            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(self._delete_selected)
            edit_layout.addWidget(delete_btn)

            layout.addWidget(edit_group)

        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        if not self.is_readonly:
            save_btn = QPushButton("Save")
            save_btn.clicked.connect(self._save_params)
            button_layout.addWidget(save_btn)

            gen_btn = QPushButton("Gen Params")
            gen_btn.setToolTip("Generate params to flow (XMeta_gen_params)")
            gen_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4A90D9;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #357ABD;
                }
            """)
            gen_btn.clicked.connect(self._gen_params)
            button_layout.addWidget(gen_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # Apply styling
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QTableView {
                border: 1px solid #ccc;
                border-radius: 4px;
                gridline-color: #e0e0e0;
            }
            QTableView::item {
                padding: 4px;
            }
            QTableView::item:selected {
                background-color: #e6f7ff;
            }
            QTableView::item:hover {
                background-color: #f5f5f5;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #4A90D9;
            }
            QPushButton {
                padding: 6px 16px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
            QPushButton:hover {
                background-color: #e6f7ff;
                border: 1px solid #4A90D9;
            }
            QPushButton:pressed {
                background-color: #cce5ff;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)

    def _debounced_filter(self, text):
        """Debounce search to avoid lag while typing"""
        self._search_debounce_timer.start(200)  # 200ms delay

    def _do_filter(self):
        """Actually perform the filter"""
        filter_text = self.search_input.text()
        if isinstance(self._model, ParamsTableModel):
            self._model.set_filter(filter_text)
            count = self._model.filtered_count()
            total = self._model.total_count()
            if filter_text:
                self.status_label.setText(f"Showing {count} of {total} parameters")
            else:
                self.status_label.setText(f"Loaded {total} parameters")

    def _clear_search(self):
        """Clear search input"""
        self.search_input.clear()
        self.search_input.setFocus()

    def _load_params(self):
        """Load parameters from file"""
        self.params_data = {}

        if not os.path.exists(self.params_file):
            self.status_label.setText(f"File not found: {self.params_file}")
            return

        try:
            with open(self.params_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    match = RE_PARAM_LINE.match(line)
                    if match:
                        param_name = match.group(1)
                        value = match.group(2).strip()
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        self.params_data[param_name] = value

            # Set data to model
            self._model.set_data(self.params_data)
            self.status_label.setText(f"Loaded {len(self.params_data)} parameters")
        except Exception as e:
            self.status_label.setText(f"Error loading file: {e}")
            logger.error(f"Error loading params file: {e}")

    def _on_double_click(self, index):
        """Handle double-click on row"""
        param_name, value = self._model.get_param(index.row())
        if param_name:
            if self.is_readonly:
                # Copy to clipboard
                clipboard = QApplication.clipboard()
                clipboard.setText(f"{param_name} = {value}")
                self.status_label.setText(f"Copied: {param_name}")
            else:
                # Populate edit panel
                self.param_input.setText(param_name)
                self.value_input.setText(str(value))
                self.param_input.setFocus()

    def _show_context_menu(self, position):
        """Show context menu"""
        index = self.table.indexAt(position)
        if not index.isValid():
            return

        param_name, value = self._model.get_param(index.row())
        if not param_name:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
            }
            QMenu::item:selected {
                background-color: #e6f7ff;
            }
        """)

        # Copy action
        copy_action = menu.addAction("📋 Copy to clipboard")
        copy_action.triggered.connect(lambda: self._copy_param(param_name, value))

        if not self.is_readonly:
            menu.addSeparator()
            edit_action = menu.addAction("✏️ Edit")
            edit_action.triggered.connect(lambda: self._edit_param(param_name, value))
            delete_action = menu.addAction("🗑️ Delete")
            delete_action.triggered.connect(lambda: self._delete_param(param_name))

        menu.exec_(self.table.viewport().mapToGlobal(position))

    def _copy_param(self, param_name, value):
        """Copy parameter to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(f"{param_name} = {value}")
        self.status_label.setText(f"Copied: {param_name}")

    def _edit_param(self, param_name, current_value):
        """Edit an existing parameter"""
        self.param_input.setText(param_name)
        self.value_input.setText(str(current_value))
        self.param_input.setFocus()

    def _add_param(self):
        """Add a new parameter"""
        param_name = self.param_input.text().strip()
        value = self.value_input.text().strip()

        if not param_name:
            self.status_label.setText("Error: Parameter name is required")
            return

        if not re.match(r'^\w+$', param_name):
            self.status_label.setText("Error: Parameter name must be alphanumeric")
            return

        self.params_data[param_name] = value
        self.modified = True

        # Refresh model
        self._model.set_data(self.params_data)
        # Re-apply current filter
        if self.search_input.text():
            self._model.set_filter(self.search_input.text())

        self.status_label.setText(f"Added parameter: {param_name}")
        self.param_input.clear()
        self.value_input.clear()

    def _update_param(self):
        """Update parameter value"""
        param_name = self.param_input.text().strip()
        value = self.value_input.text().strip()

        if not param_name:
            self.status_label.setText("Error: Parameter name is required")
            return

        if param_name in self.params_data:
            self.params_data[param_name] = value
            self.modified = True

            # Refresh model
            self._model.set_data(self.params_data)
            if self.search_input.text():
                self._model.set_filter(self.search_input.text())

            self.status_label.setText(f"Updated parameter: {param_name}")
        else:
            self.status_label.setText(f"Error: Parameter '{param_name}' not found. Use Add to create new.")

    def _delete_param(self, param_name):
        """Delete a parameter"""
        if param_name in self.params_data:
            del self.params_data[param_name]
            self.modified = True

            # Refresh model
            self._model.set_data(self.params_data)
            if self.search_input.text():
                self._model.set_filter(self.search_input.text())

            self.status_label.setText(f"Deleted parameter: {param_name}")

    def _delete_selected(self):
        """Delete selected parameter"""
        index = self.table.currentIndex()
        if not index.isValid():
            return

        param_name, _ = self._model.get_param(index.row())
        if param_name:
            self._delete_param(param_name)

    def _save_params(self):
        """Save parameters to file"""
        try:
            # Create backup
            if os.path.exists(self.params_file):
                backup_file = self.params_file + ".bak"
                shutil.copy2(self.params_file, backup_file)

            with open(self.params_file, 'w') as f:
                f.write(f"# {self.params_type.title()} Parameters\n")
                f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                for param_name, value in sorted(self.params_data.items()):
                    # Quote value if it contains spaces or special chars
                    if ' ' in value or not re.match(r'^[\w\.\-]+$', value):
                        f.write(f'{param_name} = "{value}"\n')
                    else:
                        f.write(f'{param_name} = {value}\n')

            self.modified = False
            self.status_label.setText(f"Saved to: {self.params_file}")
            logger.info(f"Saved params to: {self.params_file}")
            return True

        except Exception as e:
            self.status_label.setText(f"Error saving file: {e}")
            logger.error(f"Error saving params file: {e}")
            return False

    def _gen_params(self):
        """Execute XMeta_gen_params to generate params to flow"""
        # Check if modified and prompt to save
        if self.modified:
            reply = QMessageBox.question(
                self, 'Save Changes',
                'Parameters have been modified. Save changes before generating?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                if not self._save_params():
                    return
            elif reply == QMessageBox.Cancel:
                return
            # If No, continue with existing file

        if not self.run_dir or not os.path.exists(self.run_dir):
            self.status_label.setText(f"Error: Run directory not found: {self.run_dir}")
            QMessageBox.warning(self, "Error", f"Run directory not found:\n{self.run_dir}")
            return

        # Log the directory for debugging
        logger.info(f"Gen params - run_dir: {self.run_dir}")
        logger.info(f"Gen params - params_file: {self.params_file}")
        self.status_label.setText(f"Generating params in: {self.run_dir}")

        command = ["XMeta_gen_params"]
        command_display = f"cd {shlex.quote(self.run_dir)} && {shlex.join(command)}"
        logger.info(f"Executing: {command_display}")

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.run_dir  # Explicitly set working directory
            )
            stdout, stderr = process.communicate(timeout=60)

            if stdout:
                logger.info(stdout.decode())
            if stderr:
                logger.error(stderr.decode())

            if process.returncode == 0:
                self.status_label.setText("Params generated successfully!")
                QMessageBox.information(self, "Success", "Params generated to flow successfully!")
            else:
                self.status_label.setText(f"Gen params failed (exit code: {process.returncode})")
                QMessageBox.warning(self, "Warning", f"XMeta_gen_params exited with code {process.returncode}")

        except subprocess.TimeoutExpired:
            process.kill()
            self.status_label.setText("Error: Command timed out")
            logger.error(f"XMeta_gen_params timed out")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            logger.error(f"Error executing XMeta_gen_params: {e}")

    def closeEvent(self, event):
        """Handle close event - prompt to save if modified"""
        if self.modified and not self.is_readonly:
            reply = QMessageBox.question(
                self, 'Save Changes',
                'Parameters have been modified. Save changes?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                if not self._save_params():
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return

        event.accept()
