#!/usr/bin/env python3
"""
PyQt PDF Document Analyzer
Main entry point for the UFC/UFGS PDF analysis application.
"""

import logging
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, qInstallMessageHandler, QtMsgType, QMessageLogContext
from ui.main_window import MainWindow

# Configure root logger and uncaught exception hook
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("pillow").setLevel(logging.WARNING)
logging.getLogger("fitz").setLevel(logging.WARNING)
logging.getLogger("core").setLevel(logging.DEBUG)
logging.getLogger("ui").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)
def excepthook(exc_type, exc_value, exc_traceback):
    logging.exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
sys.excepthook = excepthook

# Install Qt message handler for logging Qt warnings/errors
def qt_message_handler(msg_type: QtMsgType, context: QMessageLogContext, message: str):
    logging.error(f"Qt {msg_type.name}: {message} ({context.file}:{context.line})")

qInstallMessageHandler(qt_message_handler)

def main():
    """Initialize and run the PDF analyzer application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("UFC PDF Document Analyzer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Criteria Assistant")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
