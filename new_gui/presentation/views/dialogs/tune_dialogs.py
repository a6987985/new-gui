from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class SelectTuneDialog(QDialog):
    """Dialog for selecting a tune file from multiple options."""
    def __init__(
        self,
        target_name,
        tune_files,
        parent=None,
        title_prefix="Select Tune",
        instruction_text="Select a tune file:",
    ):
        super().__init__(parent)
        self.target_name = target_name
        self.tune_files = tune_files  # List of (suffix, full_path)
        self.selected_tune = None
        self.instruction_text = instruction_text

        self.setWindowTitle(f"{title_prefix}: {target_name}")
        self.setMinimumWidth(350)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Instructions
        instruction_label = QLabel(self.instruction_text)
        layout.addWidget(instruction_label)

        # Create buttons for each tune file
        self.tune_buttons = {}
        for suffix, filepath in self.tune_files:
            btn = QPushButton(suffix)
            btn.setStyleSheet("text-align: left; padding: 8px;")
            btn.clicked.connect(lambda checked, s=suffix, f=filepath: self.select_tune(s, f))
            layout.addWidget(btn)
            self.tune_buttons[suffix] = btn

        # Cancel button
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)

    def select_tune(self, suffix, filepath):
        self.selected_tune = (suffix, filepath)
        self.accept()

    def get_selected_tune(self):
        return self.selected_tune


class CopyTuneSelectDialog(QDialog):
    """Dialog for selecting tune files and copying to multiple runs."""
    def __init__(self, source_run, target_name, tune_files, available_runs, parent=None):
        super().__init__(parent)
        self.source_run = source_run
        self.target_name = target_name
        self.tune_files = tune_files  # List of (suffix, full_path)
        self.available_runs = available_runs
        self.selected_tune_suffixes = []  # Changed to list for multiple selection
        self.selected_runs = []

        self.setWindowTitle(f"Copy Tune: {target_name}")
        self.setMinimumWidth(450)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Source info
        source_label = QLabel(f"Source: {self.source_run}")
        source_label.setStyleSheet("font-weight: bold; color: #4A90D9;")
        layout.addWidget(source_label)

        # Tune file selection - changed to checkboxes for multi-select
        tune_label = QLabel("Select tune files to copy:")
        layout.addWidget(tune_label)

        # Create tune file checkboxes
        self.tune_checkboxes = {}
        tune_widget = QWidget()
        tune_layout = QVBoxLayout(tune_widget)
        tune_layout.setContentsMargins(0, 0, 0, 0)

        for suffix, filepath in self.tune_files:
            cb = QCheckBox(suffix)
            cb.setChecked(True)  # Default to selected
            self.tune_checkboxes[suffix] = (cb, filepath)
            tune_layout.addWidget(cb)

        layout.addWidget(tune_widget)

        # Select/Deselect buttons for tune files
        tune_btn_layout = QHBoxLayout()
        tune_select_all_btn = QPushButton("Select All Tunes")
        tune_select_all_btn.clicked.connect(self.select_all_tunes)
        tune_deselect_all_btn = QPushButton("Deselect All Tunes")
        tune_deselect_all_btn.clicked.connect(self.deselect_all_tunes)
        tune_btn_layout.addWidget(tune_select_all_btn)
        tune_btn_layout.addWidget(tune_deselect_all_btn)
        layout.addLayout(tune_btn_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Run selection
        run_label = QLabel("Select runs to copy to:")
        layout.addWidget(run_label)

        # Create scrollable area for run list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(200)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        self.run_checkboxes = {}
        for run in sorted(self.available_runs):
            if run != self.source_run:
                cb = QCheckBox(run)
                self.run_checkboxes[run] = cb
                scroll_layout.addWidget(cb)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Select/Deselect buttons for runs
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All Runs")
        select_all_btn.clicked.connect(self.select_all_runs)
        deselect_all_btn = QPushButton("Deselect All Runs")
        deselect_all_btn.clicked.connect(self.deselect_all_runs)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        layout.addLayout(btn_layout)

        # OK/Cancel buttons
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self.accept)
        copy_btn.setStyleSheet("background-color: #4A90D9; color: white;")
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(copy_btn)
        layout.addLayout(btn_box)

    def select_all_tunes(self):
        for cb, _ in self.tune_checkboxes.values():
            cb.setChecked(True)

    def deselect_all_tunes(self):
        for cb, _ in self.tune_checkboxes.values():
            cb.setChecked(False)

    def select_all_runs(self):
        for cb in self.run_checkboxes.values():
            cb.setChecked(True)

    def deselect_all_runs(self):
        for cb in self.run_checkboxes.values():
            cb.setChecked(False)

    def get_selected_tune_suffixes(self):
        """Returns list of (suffix, filepath) tuples for selected tunes"""
        result = []
        for suffix, (cb, filepath) in self.tune_checkboxes.items():
            if cb.isChecked():
                result.append((suffix, filepath))
        return result

    def get_selected_runs(self):
        return [run for run, cb in self.run_checkboxes.items() if cb.isChecked()]


