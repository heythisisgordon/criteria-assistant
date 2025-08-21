import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from ui.pdf_viewer import PDFViewerWidget
from ui.keyword_panel import KeywordPanel
from core.annotation_system import AnnotationManager, AnnotationType
from core.keyword_provider import KeywordProvider
from core.url_provider import URLProvider
from core.config import Config

def _get_qapp():
    """Get or create a QApplication instance."""
    return QApplication.instance() or QApplication(sys.argv)

def test_pdf_viewer_minimal_init():
    """PDFViewerWidget initializes and page/zoom methods work."""
    app = _get_qapp()
    viewer = PDFViewerWidget()
    assert viewer.get_current_page() == 0
    assert abs(viewer.get_zoom_level() - Config.DEFAULT_ZOOM_LEVEL) < 0.001

    viewer.set_total_pages(5)
    # previous_page at first page should not change page
    viewer.previous_page()
    assert viewer.get_current_page() == 0

    # next_page should increment until last
    for _ in range(10):
        viewer.next_page()
    assert viewer.get_current_page() == 4  # clamps to total_pages - 1

def test_pdf_viewer_set_pixmap_no_crash():
    """Setting a QImage pixmap does not crash."""
    app = _get_qapp()
    viewer = PDFViewerWidget()
    # Create dummy 10x10 white image
    img = QImage(10, 10, QImage.Format.Format_RGB32)
    img.fill(0xFFFFFFFF)
    # Should not raise
    viewer.set_pixmap(img, page_number=0)

def test_keyword_panel_minimal_init():
    """KeywordPanel initializes and category methods do not crash."""
    app = _get_qapp()
    ann_manager = AnnotationManager()
    kp = KeywordProvider()
    up = URLProvider()
    # Register providers so categories exist
    ann_manager.register_provider(AnnotationType.KEYWORD, kp)
    ann_manager.register_provider(AnnotationType.URL_VALIDATION, up)

    panel = KeywordPanel(ann_manager, kp, up)
    # Should load categories without error
    panel.update_categories()
    panel.update_url_categories()
    # Verify category and URL checkboxes populated
    cats = set(panel.category_checkboxes.keys())
    assert cats == set(kp.get_categories())
    statuses = set(panel.url_status_checkboxes.keys())
    assert statuses == set(up.get_categories())

def test_keyword_panel_toggle_signals(qtbot):
    """Toggling categories emits appropriate signals."""
    app = _get_qapp()
    ann_manager = AnnotationManager()
    kp = KeywordProvider()
    up = URLProvider()
    ann_manager.register_provider(AnnotationType.KEYWORD, kp)
    ann_manager.register_provider(AnnotationType.URL_VALIDATION, up)

    panel = KeywordPanel(ann_manager, kp, up)
    panel.update_categories()
    panel.update_url_categories()

    # Spy category_toggled
    categories = list(kp.get_categories())
    if categories:
        with qtbot.waitSignal(panel.category_toggled, timeout=1000) as spy_cat:
            cb = panel.category_checkboxes[categories[0]]
            cb.click()  # simulate user toggle

        category, enabled = spy_cat.args
        assert category == categories[0]
        assert enabled is False

    # Spy url_status_toggled
    statuses = list(up.get_categories())
    if statuses:
        with qtbot.waitSignal(panel.url_status_toggled, timeout=1000) as spy_url:
            cbu = panel.url_status_checkboxes[statuses[0]]
            cbu.click()

        status, enabled_url = spy_url.args
        assert status == statuses[0]
        assert enabled_url is False

def test_keyword_panel_update_page_metadata():
    """update_page_metadata handles annotations and content without error."""
    app = _get_qapp()
    ann_manager = AnnotationManager()
    kp = KeywordProvider()
    up = URLProvider()
    ann_manager.register_provider(AnnotationType.KEYWORD, kp)
    ann_manager.register_provider(AnnotationType.URL_VALIDATION, up)

    panel = KeywordPanel(ann_manager, kp, up)
    panel.update_categories()
    panel.update_url_categories()

    # Fake annotations and content
    annotations = []
    content = "Test content"
    # Should not raise
    panel.update_page_metadata(0, annotations, content)
