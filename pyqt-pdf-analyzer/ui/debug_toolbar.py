import time
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QToolBar,
    QPushButton,
    QLabel,
    QSpinBox,
    QTextEdit,
    QDockWidget,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

class DebugToolbar(QToolBar):
    """Debug control toolbar for step-by-step PDF processing."""
    
    step_requested = pyqtSignal(str, dict)  # step_name, params
    
    def __init__(self, parent=None):
        super().__init__("Debug Controls", parent)
        self._setup_ui()
        
    def _setup_ui(self):
        # Step 1: Open PDF (show file dialog and emit path)
        self.btn_open = QPushButton("1. Open PDF")
        self.btn_open.clicked.connect(self._on_open_pdf)
        self.addWidget(self.btn_open)
        
        # Step 2: Get Info
        self.btn_info = QPushButton("2. Get Info")
        self.btn_info.clicked.connect(lambda: self.step_requested.emit("get_info", {}))
        self.addWidget(self.btn_info)
        
        # Page selector for steps
        self.addSeparator()
        self.addWidget(QLabel("Page:"))
        self.page_spinner = QSpinBox()
        self.page_spinner.setMinimum(0)
        self.addWidget(self.page_spinner)
        
        # Step 3: Load Page
        self.btn_load = QPushButton("3. Load Page")
        self.btn_load.clicked.connect(
            lambda: self.step_requested.emit("load_page", {"page_num": self.page_spinner.value()})
        )
        self.addWidget(self.btn_load)
        
        # Step 4: Extract Text
        self.btn_extract = QPushButton("4. Extract Text")
        self.btn_extract.clicked.connect(lambda: self.step_requested.emit("extract_text", {}))
        self.addWidget(self.btn_extract)
        
        # Step 5: Find Annotations
        self.btn_find = QPushButton("5. Find Annotations")
        self.btn_find.clicked.connect(lambda: self.step_requested.emit("find_annotations", {}))
        self.addWidget(self.btn_find)
        
        # Step 6: Render Plain
        self.btn_render = QPushButton("6. Render Plain")
        self.btn_render.clicked.connect(lambda: self.step_requested.emit("render_plain", {}))
        self.addWidget(self.btn_render)
        
        # Step 7: Apply Annotations
        self.btn_apply = QPushButton("7. Apply Annotations")
        self.btn_apply.clicked.connect(lambda: self.step_requested.emit("apply_annotations", {}))
        self.addWidget(self.btn_apply)
        
        # Step 8: Convert to QImage
        self.btn_convert = QPushButton("8. Convert to QImage")
        self.btn_convert.clicked.connect(lambda: self.step_requested.emit("convert_qimage", {}))
        self.addWidget(self.btn_convert)
        
        # Run All
        self.addSeparator()
        self.btn_all = QPushButton("Run All Steps")
        self.btn_all.clicked.connect(lambda: self.step_requested.emit("run_all", {}))
        self.addWidget(self.btn_all)
        
        # Status display
        self.addSeparator()
        self.status_label = QLabel("Ready")
        self.addWidget(self.status_label)
    
    def _on_open_pdf(self):
        """Show file dialog and emit open_document with path."""
        path, _ = QFileDialog.getOpenFileName(
            self.parent(),
            "Open PDF Document",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if path:
            self.step_requested.emit("open_document", {"path": path})
    
    def set_status(self, message: str):
        """Update status display."""
        self.status_label.setText(message)
    
    def set_page_count(self, count: int):
        """Update page spinner maximum."""
        self.page_spinner.setMaximum(count - 1)

class DebugLogWidget(QDockWidget):
    """Debug log display widget."""
    
    def __init__(self, parent=None):
        super().__init__("Debug Log", parent)
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setFont(QFont("Courier", 9))
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(QLabel("Debug Output:"))
        layout.addWidget(self.log_widget)
        self.setWidget(container)
    
    def append_log(self, message: str) -> None:
        """Add a message to the log."""
        self.log_widget.append(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def append_metrics(self, step_name: str, metrics: Dict[str, Any]) -> None:
        """Add step metrics to the log."""
        self.append_log(f"✓ {step_name}")
        self.append_log(f"  Time: {metrics['time_ms']:.2f}ms")
        self.append_log(f"  Memory delta: {metrics['memory_delta_mb']:+.2f}MB")
    
    def append_error(self, step_name: str, error: str, context: Dict[str, Any] = None) -> None:
        """Add an error to the log with optional context."""
        self.append_log(f"✗ {step_name} FAILED")
        self.append_log(f"  Error: {error}")
        if context:
            self.append_log(f"  Context: {context}")
