from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .constants import (
    APP_NAME,
    DEFAULT_CONTEXT_PROMPT,
    LANGUAGE_CODES,
    LANGUAGE_CONTEXT_PROMPTS,
    MODEL_OPTIONS,
    OUTPUT_STYLE_DESCRIPTIONS,
    PRIVACY_NOTE,
    SPEAKER_COUNT_OPTIONS,
    SUBTITLE,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from .models import TranscriptionSettings
from .transcriber import BatchTranscriptionWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.resize(1180, 760)
        self.audio_files: list[Path] = []
        self.output_dir = Path.home() / "Documents"
        self.worker: BatchTranscriptionWorker | None = None
        self.thread: QThread | None = None

        self._build_ui()
        self._connect_signals()
        self._apply_style()
        self._refresh_context_prompt()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title_row = QHBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("Title")
        version = QLabel(f"Version {__version__}")
        version.setObjectName("Version")
        title_row.addWidget(title)
        title_row.addWidget(version)
        title_row.addStretch(1)
        subtitle = QLabel(SUBTITLE)
        subtitle.setObjectName("Subtitle")
        privacy = QLabel(PRIVACY_NOTE)
        privacy.setObjectName("PrivacyNote")
        privacy.setWordWrap(True)

        root.addLayout(title_row)
        root.addWidget(subtitle)
        root.addWidget(privacy)

        toolbar_row = QHBoxLayout()
        self.add_files_button = QPushButton("Add interview files")
        self.add_folder_button = QPushButton("Add folder")
        self.remove_selected_button = QPushButton("Remove selected")
        self.clear_button = QPushButton("Clear")
        toolbar_row.addWidget(self.add_files_button)
        toolbar_row.addWidget(self.add_folder_button)
        toolbar_row.addWidget(self.remove_selected_button)
        toolbar_row.addWidget(self.clear_button)
        toolbar_row.addStretch(1)
        root.addLayout(toolbar_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["File name", "Language setting", "Duration", "Status", "Output path", "Error message"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        settings_grid = QGridLayout()
        settings_grid.setHorizontalSpacing(18)
        settings_grid.setVerticalSpacing(10)

        self.output_folder_edit = QLineEdit(str(self.output_dir))
        self.output_folder_button = QPushButton("Choose output folder")
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.output_folder_edit, 1)
        folder_row.addWidget(self.output_folder_button)
        settings_grid.addWidget(QLabel("Selected output folder"), 0, 0)
        settings_grid.addLayout(folder_row, 0, 1, 1, 3)

        self.txt_checkbox = QCheckBox("TXT")
        self.txt_checkbox.setChecked(True)
        self.docx_checkbox = QCheckBox("DOCX")
        self.docx_checkbox.setChecked(True)
        format_row = QHBoxLayout()
        format_row.addWidget(self.txt_checkbox)
        format_row.addWidget(self.docx_checkbox)
        format_row.addStretch(1)
        settings_grid.addWidget(QLabel("Output formats"), 1, 0)
        settings_grid.addLayout(format_row, 1, 1)

        self.language_combo = QComboBox()
        self.language_combo.addItems(LANGUAGE_CODES.keys())
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODEL_OPTIONS.keys())
        self.research_style_checkbox = QCheckBox("Research Transcript")
        self.research_style_checkbox.setChecked(True)
        self.timestamped_style_checkbox = QCheckBox("Timestamped Transcript")
        self.clean_style_checkbox = QCheckBox("Clean Transcript")
        self.clean_style_checkbox.setChecked(True)
        self.reading_style_checkbox = QCheckBox("Reading Transcript")
        style_row = QHBoxLayout()
        style_row.addWidget(self.research_style_checkbox)
        style_row.addWidget(self.timestamped_style_checkbox)
        style_row.addWidget(self.clean_style_checkbox)
        style_row.addWidget(self.reading_style_checkbox)
        style_row.addStretch(1)
        style_description = QLabel("\n".join(OUTPUT_STYLE_DESCRIPTIONS))
        style_description.setWordWrap(True)
        style_description.setObjectName("HelpText")

        settings_grid.addWidget(QLabel("Language"), 1, 2)
        settings_grid.addWidget(self.language_combo, 1, 3)
        settings_grid.addWidget(QLabel("Model"), 2, 0)
        settings_grid.addWidget(self.model_combo, 2, 1)
        settings_grid.addWidget(QLabel("Output styles"), 2, 2)
        settings_grid.addLayout(style_row, 2, 3)
        settings_grid.addWidget(style_description, 3, 3)
        root.addLayout(settings_grid)

        self.advanced_group = QGroupBox("Advanced Settings")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        advanced_layout = QFormLayout(self.advanced_group)

        self.context_prompt = QTextEdit()
        self.context_prompt.setMinimumHeight(86)
        self.context_prompt.setAcceptRichText(False)
        self.beam_spin = QSpinBox()
        self.beam_spin.setRange(1, 10)
        self.beam_spin.setValue(5)
        self.vad_checkbox = QCheckBox("VAD filter")
        self.vad_checkbox.setChecked(True)
        self.timestamps_checkbox = QCheckBox("Include timestamps")
        self.timestamps_checkbox.setChecked(True)
        self.filler_checkbox = QCheckBox("Keep filler words")
        self.filler_checkbox.setChecked(True)
        self.segment_combo = QComboBox()
        self.segment_combo.addItems(["Model default", "Shorter segments", "Longer segments"])
        self.json_checkbox = QCheckBox("Save JSON sidecar file")
        self.translation_checkbox = QCheckBox("Create English translation output")
        self.translation_checkbox.setToolTip(
            "Runs a second local Whisper pass and writes separate files clearly marked as machine English translation."
        )
        self.speaker_checkbox = QCheckBox("Identify speakers")
        self.speaker_checkbox.setToolTip(
            "Runs local speaker diarization and adds machine-estimated Speaker 1, Speaker 2 labels."
        )
        self.speaker_count_combo = QComboBox()
        self.speaker_count_combo.addItems(SPEAKER_COUNT_OPTIONS)

        advanced_layout.addRow("Initial prompt / context prompt", self.context_prompt)
        advanced_layout.addRow("Beam size", self.beam_spin)
        advanced_layout.addRow("", self.vad_checkbox)
        advanced_layout.addRow("", self.timestamps_checkbox)
        advanced_layout.addRow("", self.filler_checkbox)
        advanced_layout.addRow("Segment length preference", self.segment_combo)
        advanced_layout.addRow("", self.json_checkbox)
        advanced_layout.addRow("", self.translation_checkbox)
        advanced_layout.addRow("", self.speaker_checkbox)
        advanced_layout.addRow("Speakers", self.speaker_count_combo)
        root.addWidget(self.advanced_group)

        action_row = QHBoxLayout()
        self.start_button = QPushButton("Start transcription")
        self.start_button.setObjectName("PrimaryButton")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_label = QLabel("Idle")
        self.progress_label.setMinimumWidth(260)
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.progress_label)
        action_row.addWidget(self.progress, 1)
        root.addLayout(action_row)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(130)
        self.log.setPlaceholderText("Status and technical details will appear here.")
        root.addWidget(self.log)

        self.setCentralWidget(central)

        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        toolbar.addAction(quit_action)
        toolbar.hide()

    def _connect_signals(self) -> None:
        self.add_files_button.clicked.connect(self.add_files)
        self.add_folder_button.clicked.connect(self.add_folder)
        self.remove_selected_button.clicked.connect(self.remove_selected)
        self.clear_button.clicked.connect(self.clear_files)
        self.output_folder_button.clicked.connect(self.choose_output_folder)
        self.output_folder_edit.textChanged.connect(self._update_output_dir)
        self.language_combo.currentTextChanged.connect(self._language_changed)
        self.research_style_checkbox.toggled.connect(self._style_selection_changed)
        self.timestamped_style_checkbox.toggled.connect(self._style_selection_changed)
        self.clean_style_checkbox.toggled.connect(self._style_selection_changed)
        self.reading_style_checkbox.toggled.connect(self._style_selection_changed)
        self.start_button.clicked.connect(self.start_transcription)
        self.cancel_button.clicked.connect(self.cancel_transcription)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f7f5ef;
                color: #20211f;
                font-size: 14px;
            }
            QLabel#Title {
                font-size: 30px;
                font-weight: 700;
                color: #1d2a2c;
            }
            QLabel#Version {
                background: #ffffff;
                border: 1px solid #c7c1b2;
                border-radius: 6px;
                color: #4e5752;
                font-size: 12px;
                padding: 4px 8px;
            }
            QLabel#Subtitle {
                font-size: 15px;
                color: #4e5752;
            }
            QLabel#PrivacyNote {
                background: #e7efe9;
                border: 1px solid #b8c8bf;
                border-radius: 6px;
                padding: 10px 12px;
                color: #25372e;
            }
            QLabel#HelpText {
                color: #59615d;
                font-size: 12px;
            }
            QPushButton {
                border: 1px solid #9aa39b;
                border-radius: 6px;
                padding: 8px 12px;
                background: #ffffff;
            }
            QPushButton:hover {
                background: #eef2ef;
            }
            QPushButton#PrimaryButton {
                background: #23494f;
                color: #ffffff;
                border-color: #23494f;
                font-weight: 600;
            }
            QPushButton#PrimaryButton:hover {
                background: #1d3e43;
            }
            QTableWidget, QTextEdit, QLineEdit, QComboBox, QSpinBox {
                background: #ffffff;
                border: 1px solid #c7c8c1;
                border-radius: 4px;
                padding: 4px;
            }
            QHeaderView::section {
                background: #e8e4d9;
                border: 0;
                border-bottom: 1px solid #c7c1b2;
                padding: 7px;
                font-weight: 600;
            }
            QGroupBox {
                border: 1px solid #c7c1b2;
                border-radius: 6px;
                margin-top: 8px;
                padding: 10px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            """
        )

    @Slot()
    def add_files(self) -> None:
        patterns = "Audio files (*.mp3 *.wav *.m4a *.aac *.flac);;MP3 files (*.mp3);;All files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Add interview files", str(Path.home()), patterns)
        self._add_paths([Path(path) for path in files])

    @Slot()
    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add folder of interview files", str(Path.home()))
        if not folder:
            return
        paths = [
            path
            for path in sorted(Path(folder).iterdir())
            if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
        ]
        self._add_paths(paths)

    def _add_paths(self, paths: list[Path]) -> None:
        known = {path.resolve() for path in self.audio_files}
        for path in paths:
            if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
                continue
            resolved = path.resolve()
            if resolved in known:
                continue
            self.audio_files.append(resolved)
            known.add(resolved)
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._set_row(row, resolved.name, self.language_combo.currentText(), "Unknown", "Queued", "", "")
        self._log(f"Queued {len(self.audio_files)} file(s).")

    @Slot()
    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
            del self.audio_files[row]
        if rows:
            self._log(f"Removed {len(rows)} selected file(s).")

    @Slot()
    def clear_files(self) -> None:
        self.audio_files.clear()
        self.table.setRowCount(0)
        self.progress.setValue(0)
        self._log("Cleared file list.")

    @Slot()
    def choose_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", str(self.output_dir))
        if folder:
            self.output_folder_edit.setText(folder)

    @Slot(str)
    def _update_output_dir(self, value: str) -> None:
        self.output_dir = Path(value).expanduser()

    @Slot(str)
    def _language_changed(self, language: str) -> None:
        self._refresh_context_prompt()
        for row in range(self.table.rowCount()):
            self._set_cell(row, 1, language)

    @Slot()
    def _style_selection_changed(self) -> None:
        self.timestamps_checkbox.setChecked(
            self.research_style_checkbox.isChecked() or self.timestamped_style_checkbox.isChecked()
        )

    def _refresh_context_prompt(self) -> None:
        language = self.language_combo.currentText()
        self.context_prompt.setPlainText(LANGUAGE_CONTEXT_PROMPTS.get(language, DEFAULT_CONTEXT_PROMPT))

    @Slot()
    def start_transcription(self) -> None:
        if self.worker is not None:
            return
        if not self.audio_files:
            QMessageBox.warning(self, APP_NAME, "Add at least one interview file before starting transcription.")
            return
        if not self.output_dir.exists():
            QMessageBox.warning(self, APP_NAME, "Choose an available output folder before starting transcription.")
            return
        if not self.txt_checkbox.isChecked() and not self.docx_checkbox.isChecked():
            QMessageBox.warning(self, APP_NAME, "Select at least one output format: TXT or DOCX.")
            return
        output_styles = self._selected_output_styles()
        if not output_styles:
            QMessageBox.warning(self, APP_NAME, "Select at least one output style.")
            return

        settings = TranscriptionSettings(
            output_dir=self.output_dir,
            write_txt=self.txt_checkbox.isChecked(),
            write_docx=self.docx_checkbox.isChecked(),
            write_json=self.json_checkbox.isChecked(),
            model_size=MODEL_OPTIONS[self.model_combo.currentText()],
            language_label=self.language_combo.currentText(),
            language_code=LANGUAGE_CODES[self.language_combo.currentText()],
            output_styles=output_styles,
            include_timestamps=self.timestamps_checkbox.isChecked(),
            vad_filter=self.vad_checkbox.isChecked(),
            beam_size=self.beam_spin.value(),
            initial_prompt=self.context_prompt.toPlainText().strip(),
            keep_filler_words=self.filler_checkbox.isChecked(),
            segment_length_preference=self.segment_combo.currentText(),
            create_english_translation=self.translation_checkbox.isChecked(),
            identify_speakers=self.speaker_checkbox.isChecked(),
            speaker_count_label=self.speaker_count_combo.currentText(),
        )

        for row in range(self.table.rowCount()):
            self._set_cell(row, 3, "Queued")
            self._set_cell(row, 4, "")
            self._set_cell(row, 5, "")

        self.thread = QThread(self)
        self.worker = BatchTranscriptionWorker(self.audio_files[:], settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.file_started.connect(self._file_started)
        self.worker.file_progress.connect(self._file_progress)
        self.worker.duration_detected.connect(self._duration_detected)
        self.worker.file_finished.connect(self._file_finished)
        self.worker.file_failed.connect(self._file_failed)
        self.worker.batch_progress.connect(self._batch_progress)
        self.worker.overall_progress.connect(self._overall_progress)
        self.worker.log_message.connect(self._log)
        self.worker.finished.connect(self._batch_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setValue(0)
        self.progress_label.setText("Starting")
        self._log("Starting local transcription batch.")
        self.thread.start()

    @Slot()
    def cancel_transcription(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self._log("Cancellation requested. The current segment will finish before stopping.")

    @Slot(int)
    def _file_started(self, row: int) -> None:
        self._set_cell(row, 3, "Processing")
        self.progress_label.setText("Processing")

    @Slot(int, str, str, str)
    def _file_progress(self, row: int, status: str, output_path: str, error: str) -> None:
        if row < 0:
            return
        self._set_cell(row, 3, status)
        self.progress_label.setText(status)
        if output_path:
            self._set_cell(row, 4, output_path)
        if error:
            self._set_cell(row, 5, error)

    @Slot(int, str)
    def _duration_detected(self, row: int, duration: str) -> None:
        self._set_cell(row, 2, duration)

    @Slot(int, str, str)
    def _file_finished(self, row: int, status: str, output_path: str) -> None:
        self._set_cell(row, 3, status)
        self._set_cell(row, 4, output_path)
        self._set_cell(row, 5, "")
        self.progress_label.setText(status)

    @Slot(int, str)
    def _file_failed(self, row: int, error: str) -> None:
        self._set_cell(row, 3, "Failed")
        self._set_cell(row, 5, error)
        self.progress_label.setText("Failed")
        self._log(error)

    @Slot(int, int)
    def _batch_progress(self, completed: int, total: int) -> None:
        if total <= 0:
            self.progress.setValue(0)
            return
        self.progress.setValue(int((completed / total) * 100))

    @Slot(int)
    def _overall_progress(self, percent: int) -> None:
        self.progress.setValue(percent)

    @Slot()
    def _batch_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.worker = None
        self.thread = None
        self.progress.setValue(100 if self.audio_files else 0)
        self.progress_label.setText("Complete" if self.audio_files else "Idle")
        self._log("Batch finished.")

    def _set_row(
        self,
        row: int,
        file_name: str,
        language: str,
        duration: str,
        status: str,
        output_path: str,
        error: str,
    ) -> None:
        for col, value in enumerate([file_name, language, duration, status, output_path, error]):
            self._set_cell(row, col, value)

    def _set_cell(self, row: int, col: int, value: str) -> None:
        item = self.table.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, col, item)
        item.setText(value)

    def _log(self, message: str) -> None:
        if message:
            self.log.append(message)

    def _selected_output_styles(self) -> list[str]:
        styles: list[str] = []
        if self.research_style_checkbox.isChecked():
            styles.append("Research Transcript")
        if self.timestamped_style_checkbox.isChecked():
            styles.append("Timestamped Transcript")
        if self.clean_style_checkbox.isChecked():
            styles.append("Clean Transcript")
        if self.reading_style_checkbox.isChecked():
            styles.append("Reading Transcript")
        return styles
