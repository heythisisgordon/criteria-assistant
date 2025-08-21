"""
Core modules for the PyQt PDF Document Analyzer.
"""

from .config import Config
from .pdf_processor import PDFProcessor, PageMetadata

__all__ = [
    'Config',
    'PDFProcessor',
    'PageMetadata'
]
