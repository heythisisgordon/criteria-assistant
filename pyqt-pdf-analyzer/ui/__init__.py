"""
UI modules for the PyQt PDF Document Analyzer.
"""

from .main_window import MainWindow
from .pdf_viewer import PDFViewerWidget
from .keyword_panel import KeywordPanel, KeywordLegendWidget

__all__ = [
    'MainWindow',
    'PDFViewerWidget',
    'KeywordPanel',
    'KeywordLegendWidget'
]
