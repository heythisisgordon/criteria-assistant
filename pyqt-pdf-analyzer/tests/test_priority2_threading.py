import sys
import os
# Ensure project module path is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
import pytest
import fitz
from PyQt6.QtWidgets import QApplication

def _get_qapp():
    """Get or create a QApplication instance for testing."""
    return QApplication.instance() or QApplication(sys.argv)

def test_pdf_render_thread_creation():
    """PDFRenderThread can be instantiated without starting."""
    from core.pdf_processor import PDFProcessor
    from core.annotation_system import AnnotationManager
    from ui.main_window import PDFRenderThread

    manager = AnnotationManager()
    processor = PDFProcessor(manager)
    thread = PDFRenderThread(processor, page_number=0, zoom_level=1.0)
    assert thread.page_number == 0
    assert thread.zoom_level == 1.0

def test_pdf_render_thread_signals_success(qtbot):
    """Thread emits page_rendered signal on successful render."""
    app = _get_qapp()
    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor
    from ui.main_window import PDFRenderThread

    proc = PDFProcessor(AnnotationManager())
    assert proc.load_pdf("lib/ufc_word_template_05_06_2025.pdf")

    thread = PDFRenderThread(proc, page_number=0, zoom_level=1.0)
    with qtbot.waitSignal(thread.page_rendered, timeout=5000) as spy:
        thread.start()

    image, page_num = spy.args
    assert page_num == 0
    assert hasattr(image, 'width') and image.width() > 0

def test_pdf_render_thread_signals_error(qtbot):
    """Thread emits error_occurred for invalid page index."""
    app = _get_qapp()
    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor
    from ui.main_window import PDFRenderThread

    proc = PDFProcessor(AnnotationManager())
    assert proc.load_pdf("lib/ufc_word_template_05_06_2025.pdf")

    thread = PDFRenderThread(proc, page_number=9999, zoom_level=1.0)
    with qtbot.waitSignal(thread.error_occurred, timeout=5000) as spy:
        thread.start()

    err_msg, = spy.args
    assert "Failed to render page" in err_msg or "Error rendering page" in err_msg

def test_pdf_render_thread_terminate(qtbot):
    """Thread can be terminated safely while running."""
    app = _get_qapp()
    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor
    from ui.main_window import PDFRenderThread

    proc = PDFProcessor(AnnotationManager())
    assert proc.load_pdf("lib/ufc_word_template_05_06_2025.pdf")

    thread = PDFRenderThread(proc, page_number=0, zoom_level=1.0)
    thread.start()
    qtbot.wait(50)
    thread.terminate()
    thread.wait()
    assert not thread.isRunning()
