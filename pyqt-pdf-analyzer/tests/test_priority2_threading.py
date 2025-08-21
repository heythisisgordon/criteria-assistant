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

def test_pdf_render_worker_creation():
    """PDFRenderWorker can be instantiated and started."""
    from core.pdf_processor import PDFProcessor
    from core.annotation_system import AnnotationManager
    from ui.main_window import PDFRenderWorker

    manager = AnnotationManager()
    processor = PDFProcessor(manager)
    worker = PDFRenderWorker(processor)
    assert not worker.isRunning()
    worker.start()
    worker.stop()

def test_pdf_render_worker_signals_success(qtbot):
    """Worker emits page_rendered signal on successful render."""
    app = _get_qapp()
    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor
    from ui.main_window import PDFRenderWorker

    proc = PDFProcessor(AnnotationManager())
    assert proc.load_pdf("lib/ufc_word_template_05_06_2025.pdf")

    worker = PDFRenderWorker(proc)
    worker.start()
    with qtbot.waitSignal(worker.page_rendered, timeout=5000) as spy:
        worker.request_render(0, 1.0)

    image, page_num = spy.args
    assert page_num == 0
    assert hasattr(image, 'width') and image.width() > 0
    worker.stop()

def test_pdf_render_worker_signals_error(qtbot):
    """Worker emits error_occurred for invalid page index."""
    app = _get_qapp()
    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor
    from ui.main_window import PDFRenderWorker

    proc = PDFProcessor(AnnotationManager())
    assert proc.load_pdf("lib/ufc_word_template_05_06_2025.pdf")

    worker = PDFRenderWorker(proc)
    worker.start()
    with qtbot.waitSignal(worker.error_occurred, timeout=5000) as spy:
        worker.request_render(9999, 1.0)

    err_msg, = spy.args
    assert "Failed to render page" in err_msg or "Error rendering page" in err_msg
    worker.stop()

def test_pdf_render_worker_stop(qtbot):
    """Worker can be stopped safely while running."""
    app = _get_qapp()
    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor
    from ui.main_window import PDFRenderWorker

    proc = PDFProcessor(AnnotationManager())
    assert proc.load_pdf("lib/ufc_word_template_05_06_2025.pdf")

    worker = PDFRenderWorker(proc)
    worker.start()
    qtbot.wait(50)
    worker.stop()
    assert not worker.isRunning()
