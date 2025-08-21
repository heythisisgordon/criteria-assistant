# Plan: Priority 3 – PyQt Widget Initialization Tests

## Objectives
Validate that key UI widgets initialize and operate without crashing:
- PDFViewerWidget  
- KeywordPanel  

## Test File
Location: `pyqt-pdf-analyzer/tests/test_priority3_widgets.py`  
Framework: pytest + pytest-qt

## Common Setup
```python
import sys, os
import pytest
from PyQt6.QtWidgets import QApplication

# Ensure project root on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

def _get_qapp():
    """Get or create a QApplication instance."""
    return QApplication.instance() or QApplication(sys.argv)
```

## Tests

### 1. test_pdf_viewer_minimal_init
- Instantiate `PDFViewerWidget()`.
- Assert default `get_current_page() == 0`.
- Assert default `get_zoom_level() == Config.DEFAULT_ZOOM_LEVEL`.
- Call `set_total_pages(5)`; assert page count updated.
- Call `previous_page()` at first page; assert page remains 0.
- Call `next_page()` repeatedly; assert page clamps to last index.

### 2. test_pdf_viewer_set_pixmap_no_crash
- Create a 10×10 white `QImage`.
- Call `PDFViewerWidget().set_pixmap(dummy_image)`.
- Assert no exception is raised.

### 3. test_keyword_panel_minimal_init
- Instantiate `KeywordPanel(annotation_manager, keyword_provider, url_provider)` with fresh providers.
- Call `update_categories()` and `update_url_categories()`.
- Assert `get_categories()` returns provider categories without error.

### 4. test_keyword_panel_toggle_signals
- Use `qtbot` to spy on `category_toggled` and `url_status_toggled`.
- Toggle a single category via `provider.set_category_enabled("SomeCategory", False)`.
- Assert the widget emits `category_toggled` with correct args.
- Similarly toggle a URL status and assert `url_status_toggled`.

### 5. test_keyword_panel_update_page_metadata
- Create a fake annotation list and content string.
- Call `update_page_metadata(0, annotations, content)`.
- Assert widget updates internal display state without error.

## Execution Order
1. test_pdf_viewer_minimal_init  
2. test_pdf_viewer_set_pixmap_no_crash  
3. test_keyword_panel_minimal_init  
4. test_keyword_panel_toggle_signals  
5. test_keyword_panel_update_page_metadata
