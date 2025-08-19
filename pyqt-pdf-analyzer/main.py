#!/usr/bin/env python3
"""
PyQt PDF Document Analyzer
Main entry point for the UFC/UFGS PDF analysis application.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow

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
