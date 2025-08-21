import sys
import os
# Ensure project root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import pytest
import fitz
from PyQt6.QtWidgets import QApplication

def _get_qapp():
    """Get or create a QApplication instance for testing."""
    return QApplication.instance() or QApplication(sys.argv)

def test_pdf_processor_minimal_creation():
    """Test PDFProcessor can be instantiated with minimal setup."""
    app = _get_qapp()
    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor

    annotation_manager = AnnotationManager()
    processor = PDFProcessor(annotation_manager)
    assert processor is not None

def test_annotation_components_individual_imports():
    """Test each annotation system component can be imported without error."""
    modules = [
        "core.annotation_system",
        "core.keyword_provider",
        "core.url_provider",
        "core.annotation_renderers",
    ]
    for module in modules:
        __import__(module)

def test_providers_load_data_isolation(tmp_path, caplog):
    """Test providers handle missing or valid data gracefully."""
    from core.keyword_provider import KeywordProvider
    from core.url_provider import URLProvider

    kp = KeywordProvider()
    up = URLProvider()

    # Non-existent files should return False
    assert kp.load_data("nonexistent.csv") is False
    assert up.load_data("nonexistent.csv") is False

    # Default paths should load or return bool without exception
    result_kp = kp.load_data()
    result_up = up.load_data()
    assert isinstance(result_kp, bool)
    assert isinstance(result_up, bool)

def test_fitz_pdf_opening_direct():
    """Test PyMuPDF can open a known PDF and extract text."""
    test_pdf = "lib/ufc_word_template_05_06_2025.pdf"
    doc = fitz.open(test_pdf)
    try:
        assert len(doc) > 0
        page = doc.load_page(0)
        text = page.get_text()
        assert isinstance(text, str)
    finally:
        doc.close()

def test_pdf_processor_controlled_initialization():
    """Integration: step-by-step PDFProcessor initialization and PDF load."""
    app = _get_qapp()
    from core.annotation_system import AnnotationManager
    try:
        from core.keyword_manager import KeywordManager
        keyword_manager = KeywordManager()
    except ImportError:
        from core.annotation_system import AnnotationManager
        keyword_manager = AnnotationManager()

    from core.pdf_processor import PDFProcessor

    processor = PDFProcessor(keyword_manager)
    loaded = processor.load_pdf("lib/ufc_word_template_05_06_2025.pdf")
    assert loaded is True
    assert processor.get_page_count() > 0
