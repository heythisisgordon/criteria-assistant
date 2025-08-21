# Plan: Priority 2 – Threading (PDFRenderThread) Unit Tests

## Objectives

Isolate and validate behavior of `PDFRenderThread` to pinpoint crashes in worker threads:
1. Creation and basic attributes
2. Correct signal emissions when rendering succeeds
3. Correct error handling when rendering fails
4. Thread lifecycle (start, finish, terminate)

## Test File

- Location: `pyqt-pdf-analyzer/tests/test_priority2_threading.py`
- Framework: pytest + PyQt6 (with Qt event loop stub where needed)

## Detailed Tests

### 1. Test Thread Creation

```python
def test_pdf_render_thread_creation():
    """PDFRenderThread can be instantiated without starting."""
    from core.pdf_processor import PDFProcessor
    from core.annotation_system import AnnotationManager
    from ui.main_window import PDFRenderThread

    # Minimal setup
    pm = PDFProcessor(AnnotationManager())
    thread = PDFRenderThread(pm, page_number=0, zoom_level=1.0)
    assert thread.page_number == 0
    assert thread.zoom_level == 1.0
```

### 2. Test Successful Render Signals

```python
def test_pdf_render_thread_signals_success(qtbot, tmp_path):
    """Thread emits page_rendered signal on successful render."""
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor
    from ui.main_window import PDFRenderThread

    # Load a known PDF
    proc = PDFProcessor(AnnotationManager())
    proc.load_pdf("lib/ufc_word_template_05_06_2025.pdf")

    # Create thread and connect to qtbot signal spy
    thread = PDFRenderThread(proc, page_number=0, zoom_level=1.0)
    spy = qtbot.waitSignal(thread.page_rendered, timeout=5000)

    thread.start()
    qtbot.wait(100)  # allow thread to queue signals

    # Verify we received the signal
    image, page_num = spy.args
    assert page_num == 0
    assert hasattr(image, 'width') and image.width() > 0
```

### 3. Test Render Failure Signals

```python
def test_pdf_render_thread_signals_error(qtbot):
    """Thread emits error_occurred for invalid page index."""
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor
    from ui.main_window import PDFRenderThread

    proc = PDFProcessor(AnnotationManager())
    proc.load_pdf("lib/ufc_word_template_05_06_2025.pdf")

    # Use out-of-range page number
    thread = PDFRenderThread(proc, page_number=9999, zoom_level=1.0)
    spy = qtbot.waitSignal(thread.error_occurred, timeout=5000)

    thread.start()
    qtbot.wait(100)

    err_msg, = spy.args
    assert "Failed to render page" in err_msg or "Error rendering page" in err_msg
```

### 4. Test Thread Termination

```python
def test_pdf_render_thread_terminate(qtbot):
    """Thread can be terminated safely while running."""
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    from core.annotation_system import AnnotationManager
    from core.pdf_processor import PDFProcessor
    from ui.main_window import PDFRenderThread

    proc = PDFProcessor(AnnotationManager())
    proc.load_pdf("lib/ufc_word_template_05_06_2025.pdf")

    thread = PDFRenderThread(proc, page_number=0, zoom_level=1.0)
    thread.start()
    qtbot.wait(50)  # let thread start work
    thread.terminate()
    thread.wait()
    assert not thread.isRunning()
```

## Execution Order

1. `test_pdf_render_thread_creation`  
2. `test_pdf_render_thread_signals_success`  
3. `test_pdf_render_thread_signals_error`  
4. `test_pdf_render_thread_terminate`

This suite will confirm whether the threading model is responsible for the crash and how signals behave under error conditions.
