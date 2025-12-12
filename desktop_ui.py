import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QRadioButton, QGroupBox, QSizePolicy, QScrollArea,
    QPushButton, QFileDialog, QMessageBox, QDialog, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit, QSplitter,
    QSpinBox, QComboBox, QFormLayout
)
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

from summarizer_logic import process_text
from document_handler import extract_text_from_pdf, extract_text_from_docx
from database_manager import init_db, save_summary_record, get_history, delete_record

class AIWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, text, mode, task_type, api_key, num_questions=5, difficulty="Medium"):
        super().__init__()
        self.text = text
        self.mode = mode
        self.task_type = task_type
        self.api_key = api_key
        self.num_questions = num_questions
        self.difficulty = difficulty

    def run(self):
        try:
            result = process_text(
                self.text, 
                self.mode, 
                self.task_type, 
                self.api_key, 
                self.num_questions, 
                self.difficulty
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class QuizConfigDialog(QDialog):
    """Popup to configure Quiz settings."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quiz Configuration")
        self.resize(300, 150)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.num_q_spin = QSpinBox()
        self.num_q_spin.setRange(1, 20)
        self.num_q_spin.setValue(5)
        
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Easy", "Medium", "Hard", "Expert"])
        self.difficulty_combo.setCurrentIndex(1) 
        
        form_layout.addRow("Number of Questions:", self.num_q_spin)
        form_layout.addRow("Difficulty:", self.difficulty_combo)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Generate")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("""
            QDialog { background-color: rgb(35, 36, 45); color: white; }
            QLabel { color: white; font-size: 14px; }
            QSpinBox, QComboBox { 
                background-color: rgb(24, 25, 30); 
                color: white; 
                padding: 5px; 
                border: 1px solid rgb(55, 60, 75); 
                border-radius: 4px;
            }
            QPushButton { background-color: rgb(70, 70, 80); color: white; border: none; padding: 8px 15px; border-radius: 5px; }
            QPushButton:hover { background-color: rgb(90, 90, 100); }
        """)

    def get_values(self):
        return self.num_q_spin.value(), self.difficulty_combo.currentText()

class HistoryDetailDialog(QDialog):
    def __init__(self, input_text, output_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("History Details")
        self.resize(700, 500)
        self.setup_ui(input_text, output_text)

    def setup_ui(self, input_text, output_text):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Vertical)
        
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0,0,0,0)
        input_layout.addWidget(QLabel("<b>Original Input:</b>"))
        input_edit = QTextEdit()
        input_edit.setPlainText(input_text)
        input_edit.setReadOnly(True)
        input_layout.addWidget(input_edit)
        splitter.addWidget(input_widget)
        
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0,0,0,0)
        output_layout.addWidget(QLabel("<b>Generated Result:</b>"))
        output_edit = QTextEdit()
        output_edit.setPlainText(output_text)
        output_edit.setReadOnly(True)
        output_layout.addWidget(output_edit)
        splitter.addWidget(output_widget)
        
        layout.addWidget(splitter)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setStyleSheet("""
            QDialog, QWidget { background-color: rgb(35, 36, 45); color: white; }
            QTextEdit { background-color: rgb(24, 25, 30); color: rgb(220, 220, 220); border: 1px solid rgb(55, 60, 75); padding: 10px; }
            QLabel { color: rgb(150, 150, 150); font-size: 14px; margin-bottom: 5px; }
            QPushButton { background-color: rgb(70, 70, 80); color: white; border: none; padding: 8px 15px; border-radius: 5px; }
            QPushButton:hover { background-color: rgb(90, 90, 100); }
        """)

class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("History")
        self.resize(900, 600)
        self.full_records = [] 
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Double-click a row to view full details.")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Time", "Input Preview", "Result Preview", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.view_details)
        
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setStyleSheet("background-color: rgb(180, 60, 60);")
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch(1)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("""
            QDialog { background-color: rgb(35, 36, 45); color: white; }
            QTableWidget { background-color: rgb(24, 25, 30); color: rgb(220, 220, 220); border: 1px solid rgb(55, 60, 75); gridline-color: rgb(55, 60, 75); }
            QHeaderView::section { background-color: rgb(45, 45, 50); color: white; padding: 5px; border: 1px solid rgb(55, 60, 75); }
            QPushButton { background-color: rgb(70, 70, 80); color: white; border: none; padding: 8px 15px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: rgb(90, 90, 100); }
            
            QScrollBar:vertical { border: none; background: rgb(35, 36, 45); width: 14px; margin: 0px; }
            QScrollBar::handle:vertical { background: rgb(80, 80, 90); min-height: 20px; border-radius: 7px; margin: 2px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

    def load_data(self):
        self.full_records = get_history()
        self.table.setRowCount(len(self.full_records))
        for row, (rec_id, timestamp, inp, out, mode) in enumerate(self.full_records):
            self.table.setItem(row, 0, QTableWidgetItem(str(rec_id)))
            self.table.setItem(row, 1, QTableWidgetItem(timestamp[:16].replace('T', ' ')))
            input_preview = (inp[:50] + '...') if len(inp) > 50 else inp
            self.table.setItem(row, 2, QTableWidgetItem(input_preview))
            output_preview = (out[:50] + '...') if len(out) > 50 else out
            self.table.setItem(row, 3, QTableWidgetItem(output_preview))
            self.table.setItem(row, 4, QTableWidgetItem(mode))

    def view_details(self):
        row = self.table.currentRow()
        if row >= 0:
            _, _, full_input, full_output, _ = self.full_records[row]
            detail_dialog = HistoryDetailDialog(full_input, full_output, self)
            detail_dialog.exec_()

    def delete_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            rec_id = self.full_records[row][0]
            confirm = QMessageBox.question(
                self, "Confirm Delete", 
                "Are you sure you want to delete this record?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                delete_record(rec_id)
                self.load_data()

class DarkApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Processing Configurator")
        self.setup_dark_theme()
        self.create_widgets()
        init_db() 
        self.thread = None
        self.worker = None

    def setup_dark_theme(self):
        dark_palette = QPalette()
        background_color = QColor(24, 25, 30)
        text_color = QColor(220, 220, 220)
        highlight_color = QColor(135, 140, 250)
        dark_palette.setColor(QPalette.Window, background_color)
        dark_palette.setColor(QPalette.WindowText, text_color)
        dark_palette.setColor(QPalette.Base, QColor(35, 36, 45))
        dark_palette.setColor(QPalette.Text, text_color)
        dark_palette.setColor(QPalette.Button, background_color)
        dark_palette.setColor(QPalette.ButtonText, text_color)
        dark_palette.setColor(QPalette.Highlight, highlight_color)
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(dark_palette)
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: rgb(24, 25, 30); }
            QLabel { color: rgb(220, 220, 220); font-size: 15px; font-family: 'Segoe UI', sans-serif; }
            QTextEdit, QLineEdit { background-color: rgb(35, 36, 45); color: rgb(240, 240, 240); border: 2px solid rgb(55, 60, 75); padding: 12px; border-radius: 10px; font-size: 16px; font-family: 'Segoe UI', sans-serif; }
            QGroupBox { border: 1px solid rgb(55, 60, 75); border-radius: 8px; margin-top: 10px; padding-top: 15px; font-family: 'Segoe UI', sans-serif; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; color: rgb(150, 150, 150); font-weight: bold; }
            QRadioButton { color: rgb(220, 220, 220); padding: 5px 0; font-family: 'Segoe UI', sans-serif; }
            QRadioButton::indicator { width: 16px; height: 16px; }
            QPushButton { background-color: rgb(135, 140, 250); color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 16px; font-weight: bold; font-family: 'Segoe UI', sans-serif; }
            QPushButton:hover { background-color: rgb(150, 155, 255); }
            #processButton { background-color: rgb(30, 200, 150); }
            #processButton:hover { background-color: rgb(50, 220, 170); }
            #saveButton { background-color: rgb(70, 150, 100); }
            #saveButton:hover { background-color: rgb(90, 170, 120); }
            #historyButton { background-color: rgb(100, 100, 120); }
            #historyButton:hover { background-color: rgb(120, 120, 140); }
            
            QScrollBar:vertical { border: none; background: rgb(35, 36, 45); width: 14px; margin: 0px; }
            QScrollBar::handle:vertical { background: rgb(80, 80, 90); min-height: 20px; border-radius: 7px; margin: 2px; }
            QScrollBar::handle:vertical:hover { background: rgb(100, 100, 110); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

    def create_widgets(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_scroll_area = QScrollArea()
        main_scroll_area.setWidgetResizable(True)
        main_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_scroll_area.setFrameShape(QScrollArea.NoFrame)
        main_scroll_area.verticalScrollBar().setSingleStep(10)
        
        scroll_content = QWidget()
        main_scroll_area.setWidget(scroll_content)
        main_layout = QVBoxLayout(scroll_content)
        main_layout.setContentsMargins(70, 50, 70, 50)
        main_layout.setSpacing(25)

        api_layout = QHBoxLayout()
        api_label = QLabel("Google API Key:")
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setPlaceholderText("Paste your Gemini API Key here... (Or leave empty if using Environment Variable)")
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_input)
        main_layout.addLayout(api_layout)

        top_bar_layout = QHBoxLayout()
        
        mode_group = QGroupBox("Processing Mode")
        mode_group.setFont(QFont("Segoe UI", 11))
        mode_layout = QHBoxLayout(mode_group)
        self.speed_radio = QRadioButton("Speed (Flash)")
        self.speed_radio.setChecked(True)
        self.accuracy_radio = QRadioButton("Accuracy (Pro)")
        mode_layout.addWidget(self.speed_radio)
        mode_layout.addWidget(self.accuracy_radio)
        
        task_group = QGroupBox("Action")
        task_group.setFont(QFont("Segoe UI", 11))
        task_layout = QHBoxLayout(task_group)
        self.task_summary_radio = QRadioButton("Summarize")
        self.task_summary_radio.setChecked(True)
        self.task_mcq_radio = QRadioButton("Generate Quiz")
        task_layout.addWidget(self.task_summary_radio)
        task_layout.addWidget(self.task_mcq_radio)
        
        top_bar_layout.addWidget(mode_group)
        top_bar_layout.addWidget(task_group)
        top_bar_layout.addStretch(1)
        
        self.history_button = QPushButton("View History")
        self.history_button.setObjectName("historyButton")
        self.history_button.setFixedWidth(150)
        self.history_button.clicked.connect(self.open_history)
        top_bar_layout.addWidget(self.history_button)
        
        main_layout.addLayout(top_bar_layout)
        
        input_header_layout = QHBoxLayout()
        input_label = QLabel("Input Source:")
        self.upload_button = QPushButton("Upload Document")
        self.upload_button.setCursor(Qt.PointingHandCursor)
        self.upload_button.clicked.connect(self.handle_file_upload)
        input_header_layout.addWidget(input_label)
        input_header_layout.addStretch(1)
        input_header_layout.addWidget(self.upload_button)
        main_layout.addLayout(input_header_layout)
        
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Paste text or upload a document...")
        self.text_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.text_input.setMinimumHeight(200)
        main_layout.addWidget(self.text_input)
        
        self.process_button = QPushButton("Run AI Processor")
        self.process_button.setCursor(Qt.PointingHandCursor)
        self.process_button.setObjectName("processButton") 
        self.process_button.clicked.connect(self.handle_processing)
        main_layout.addWidget(self.process_button)
        
        output_label = QLabel("Generated Output:")
        main_layout.addWidget(output_label)
        self.summary_output = QTextEdit()
        self.summary_output.setReadOnly(True)
        self.summary_output.setPlaceholderText("Output will appear here...")
        self.summary_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.summary_output.setMinimumHeight(250)
        main_layout.addWidget(self.summary_output)
        
        action_layout = QHBoxLayout()
        action_layout.addStretch(1)
        self.save_button = QPushButton("Save Chat to History")
        self.save_button.setObjectName("saveButton")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self.save_current_chat)
        self.save_button.setEnabled(False) 
        action_layout.addWidget(self.save_button)
        main_layout.addLayout(action_layout)
        
        layout_container = QVBoxLayout(central_widget)
        layout_container.setContentsMargins(0,0,0,0)
        layout_container.addWidget(main_scroll_area)

    def handle_file_upload(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Document", "", "Documents (*.txt *.pdf *.docx);;All Files (*)", options=options
        )
        if file_path:
            text_content = ""
            try:
                if file_path.lower().endswith('.pdf'):
                    text_content = extract_text_from_pdf(file_path)
                elif file_path.lower().endswith('.docx'):
                    text_content = extract_text_from_docx(file_path)
                elif file_path.lower().endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                self.text_input.setText(text_content)
                self.summary_output.setText(f"Loaded: {os.path.basename(file_path)}")
                self.save_button.setEnabled(False)
            except Exception as e:
                self.summary_output.setText(f"Error loading file: {str(e)}")

    def handle_processing(self):
        input_text = self.text_input.toPlainText()
        api_key = self.api_input.text().strip()

        if not input_text.strip():
            self.summary_output.setText("Please provide input text.")
            return
        
        if not api_key and not os.environ.get("GEMINI_API_KEY"):
            self.summary_output.setText("Error: Please enter your Google API Key above or set GEMINI_API_KEY environment variable.")
            return

        mode = "speed" if self.speed_radio.isChecked() else "accuracy"
        task_type = "mcq" if self.task_mcq_radio.isChecked() else "summary"
        
        num_questions = 5
        difficulty = "Medium"
        
        if task_type == "mcq":
            config_dialog = QuizConfigDialog(self)
            if config_dialog.exec_() == QDialog.Accepted:
                num_questions, difficulty = config_dialog.get_values()
            else:
                return 

        self.summary_output.setText("Connecting to Cloud API... Please wait...")
        self.process_button.setEnabled(False)
        self.process_button.setText("Processing...")
        
        self.thread = QThread()

        self.worker = AIWorker(input_text, mode, task_type, api_key, num_questions, difficulty)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error.connect(self.on_processing_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_processing_finished(self, result):
        self.summary_output.setText(result)
        self.save_button.setEnabled(True)
        self.process_button.setEnabled(True)
        self.process_button.setText("Run AI Processor")

    def on_processing_error(self, error_msg):
        self.summary_output.setText(f"Error: {error_msg}")
        self.process_button.setEnabled(True)
        self.process_button.setText("Run AI Processor")

    def save_current_chat(self):
        input_text = self.text_input.toPlainText()
        output_text = self.summary_output.toPlainText()
        mode = "speed" if self.speed_radio.isChecked() else "accuracy"
        task = "Quiz" if self.task_mcq_radio.isChecked() else "Summary"
        save_mode = f"{mode} | {task}"
        
        if input_text and output_text:
            save_summary_record(input_text, output_text, save_mode)
            QMessageBox.information(self, "Saved", "Chat has been saved to history.")
            self.save_button.setEnabled(False)

    def open_history(self):
        dialog = HistoryDialog(self)
        dialog.exec_()

def run_ui_setup():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    window = DarkApp()
    window.showMaximized()
    sys.exit(app.exec_())