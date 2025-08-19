"""
Core modules for the PyQt PDF Document Analyzer.
"""

from .config import Config
from .keyword_manager import KeywordManager, Keyword
from .pdf_processor import PDFProcessor, PageMetadata

__all__ = [
    'Config',
    'KeywordManager', 
    'Keyword',
    'PDFProcessor',
    'PageMetadata'
]
