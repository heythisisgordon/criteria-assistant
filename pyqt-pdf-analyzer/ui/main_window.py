"""
Main window for the PyQt PDF Document Analyzer.
"""

import logging
import os
import queue
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QMenuBar, QMenu, QStatusBar, QFileDialog,
    QMessageBox, QSplitter, QProgressBar, QLabel,
    QToolBar, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QImage
from typing import Optional, Dict, Any

from core.config import Config
from core.keyword_provider import KeywordProvider
from core.url_provider import URLProvider
from core.annotation_system import AnnotationManager, AnnotationType
from core.pdf_processor import PDFProcessor
from core.page_metadata import PageMetadata
from core.debug_processor import DebugPDFProcessor
from ui.debug_toolbar import DebugToolbar, DebugLogWidget
from ui.pdf_viewer import PDFViewerWidget
from ui.keyword_panel import KeywordPanel


class PDFRenderWorker(QThread):
    """Long-lived thread processing queued page render requests."""
    page_rendered = pyqtSignal(QImage, int)
    error_occurred = pyqtSignal(str)

    def __init__(self, pdf_processor: PDFProcessor):
        super().__init__()
        self.pdf_processor = pdf_processor
        self._queue: "queue.Queue[tuple[int, float]]" = queue.Queue()
        self._running = True

    @pyqtSlot(int, float)
    def request_render(self, page_number: int, zoom_level: float) -> None:
        """Queue a page render request, keeping only the most recent one."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._queue.put((page_number, zoom_level))

    def run(self) -> None:
        while self._running:
            page_number, zoom_level = self._queue.get()
            if page_number is None:
                break
            try:
                image = self.pdf_processor.render_page(page_number, zoom_level)
                if image:
                    self.page_rendered.emit(image, page_number)
                else:
                    self.error_occurred.emit(
                        f"Failed to render page {page_number + 1}")
            except Exception as e:
                logging.exception("Error rendering page")
                self.error_occurred.emit(f"Error rendering page: {str(e)}")

    def stop(self) -> None:
        self._running = False
        self._queue.put((None, 0.0))
        self.wait()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        # Initialize annotation framework
        self.annotation_manager = AnnotationManager()
        self.keyword_provider = KeywordProvider()
        self.url_provider = URLProvider()
        # Register providers
        self.annotation_manager.register_provider(
            AnnotationType.KEYWORD, self.keyword_provider)
        self.annotation_manager.register_provider(
            AnnotationType.URL_VALIDATION, self.url_provider)
        # Register renderers inside PDFProcessor
        self.pdf_processor = DebugPDFProcessor(self.annotation_manager)
        self.render_thread = PDFRenderWorker(self.pdf_processor)

        # UI components
        self.pdf_viewer: Optional[PDFViewerWidget] = None
        self.keyword_panel: Optional[KeywordPanel] = None
        self.status_bar: Optional[QStatusBar] = None
        self.progress_bar: Optional[QProgressBar] = None

        self._setup_ui()
        self._setup_connections()
        # Render worker connections
        self.render_thread.page_rendered.connect(self.pdf_viewer.set_pixmap)
        self.render_thread.error_occurred.connect(self._on_pdf_error)
        self.render_thread.start()

        # Debounce timer for render requests
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_current_page)

        # Debug UI integration
        self.debug_toolbar = DebugToolbar(self)
        self.addToolBar(self.debug_toolbar)
        self.debug_log_widget = DebugLogWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.debug_log_widget)
        # Connect debug signals
        self.debug_toolbar.step_requested.connect(self._on_debug_step)
        self.pdf_processor.step_completed.connect(
            self.debug_log_widget.append_metrics)
        self.pdf_processor.step_failed.connect(
            self.debug_log_widget.append_error)
        self.pdf_processor.step_completed.connect(
            lambda name, metrics: self.debug_toolbar.set_status(f"{name} ✓"))
        self.pdf_processor.step_failed.connect(
            lambda name, err, ctx: self.debug_toolbar.set_status(f"{name} ✗"))

        # Load default data
        logging.debug(f"MainWindow.__init__: loading keywords from {self.keyword_provider.get_default_source_path()}")
        self.keyword_provider.load_data()
        logging.debug(f"MainWindow.__init__: keywords loaded: {self.keyword_provider.get_enabled_categories()}")
        logging.debug(f"MainWindow.__init__: loading URL validations from {self.url_provider.get_default_source_path()}")
        self.url_provider.load_data()
        logging.debug(f"MainWindow.__init__: URL validations loaded: {self.url_provider.get_enabled_categories()}")
        self.keyword_panel.update_categories()
        self.keyword_panel.update_url_categories()

        self.setWindowTitle("UFC PDF Document Analyzer")
        self.setMinimumSize(
            Config.DEFAULT_WINDOW_WIDTH,
            Config.DEFAULT_WINDOW_HEIGHT)
        self.resize(Config.DEFAULT_WINDOW_WIDTH, Config.DEFAULT_WINDOW_HEIGHT)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        # Keyword panel
        self.keyword_panel = KeywordPanel(
            self.annotation_manager,
            self.keyword_provider,
            self.url_provider
        )
        self.keyword_panel.setMinimumWidth(300)
        self.keyword_panel.setMaximumWidth(400)
        splitter.addWidget(self.keyword_panel)
        # PDF viewer
        self.pdf_viewer = PDFViewerWidget()
        splitter.addWidget(self.pdf_viewer)
        splitter.setSizes([300, 900])
        main_layout.addWidget(splitter)
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()

    def _create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        open_action = QAction("&Open PDF...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_pdf)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        load_keywords_action = QAction("Load &Keywords...", self)
        load_keywords_action.triggered.connect(self.load_keywords)
        file_menu.addAction(load_keywords_action)
        load_urls_action = QAction("Load &URL Validations...", self)
        load_urls_action.triggered.connect(self.load_url_validations)
        file_menu.addAction(load_urls_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        view_menu = menubar.addMenu("&View")
        view_menu.addAction(
            QAction(
                "Zoom &In",
                self,
                triggered=self.pdf_viewer.zoom_in))
        view_menu.addAction(
            QAction(
                "Zoom &Out",
                self,
                triggered=self.pdf_viewer.zoom_out))
        view_menu.addAction(
            QAction(
                "&Fit to Width",
                self,
                triggered=self.pdf_viewer.fit_to_width))
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self, triggered=self.show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        toolbar.addAction(QAction("Open PDF", self, triggered=self.open_pdf))
        toolbar.addSeparator()
        toolbar.addAction(
            QAction(
                "◀ Previous",
                self,
                triggered=self.pdf_viewer.previous_page))
        toolbar.addAction(
            QAction(
                "Next ▶",
                self,
                triggered=self.pdf_viewer.next_page))

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage(
            "Ready - Load a PDF document to begin analysis")

    def _setup_connections(self):
        self.pdf_viewer.page_changed.connect(self._on_page_changed)
        self.pdf_viewer.zoom_changed.connect(self._on_zoom_changed)
        self.keyword_panel.category_toggled.connect(self._on_category_toggled)
        self.keyword_panel.url_status_toggled.connect(
            self._on_url_status_toggled)
        self.keyword_panel.search_changed.connect(self._on_search_changed)
        self.keyword_panel.refresh_requested.connect(self._refresh_annotations)
        self.pdf_processor.error_occurred.connect(self._on_pdf_error)

    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF Document", "", "PDF Files (*.pdf);;All Files (*)")
        if path:
            self._load_pdf(path)

    def _load_pdf(self, file_path: str):
        logging.debug(f"MainWindow._load_pdf: start loading PDF at {file_path}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage("Loading PDF...")
        if self.pdf_processor.load_pdf(file_path):
            logging.debug(f"MainWindow._load_pdf: PDF loaded successfully with {self.pdf_processor.get_page_count()} pages")
            count = self.pdf_processor.get_page_count()
            self.pdf_viewer.set_total_pages(count)
            self._render_current_page()
            self.debug_toolbar.set_page_count(count)
            self.setWindowTitle(
                f"UFC PDF Document Analyzer - {os.path.basename(file_path)}")
            self.status_bar.showMessage(
                f"Loaded PDF: {
                    os.path.basename(file_path)} ({count} pages)")
        else:
            logging.error(f"MainWindow._load_pdf: failed to load PDF at {file_path}")
            QMessageBox.critical(
                self,
                "Error Loading PDF",
                f"Could not load PDF:\n{file_path}")
            self.status_bar.showMessage("Failed to load PDF")
        self.progress_bar.setVisible(False)

    def load_keywords(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Keywords CSV", "", "CSV Files (*.csv);;All Files (*)")
        if path and self.keyword_provider.load_data(path):
            self.keyword_panel.update_categories()
            self.status_bar.showMessage(
                f"Keywords loaded from: {
                    os.path.basename(path)}")
            self._render_current_page()

    def load_url_validations(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load URL Validations CSV", "", "CSV Files (*.csv);;All Files (*)")
        if path and self.url_provider.load_data(path):
            self.keyword_panel.update_url_categories()
            self.status_bar.showMessage(
                f"URL validations loaded from: {
                    os.path.basename(path)}")
            self._render_current_page()

    def _render_current_page(self):
        if not self.pdf_processor.document:
            return
        page = self.pdf_viewer.get_current_page()
        zoom = self.pdf_viewer.get_zoom_level()
        self.render_thread.request_render(page, zoom)
        self._update_page_metadata(page)

    def _on_page_changed(self, page_number: int):
        self._render_timer.start(150)
        self.status_bar.showMessage(f"Page {page_number + 1}")

    def _on_zoom_changed(self, zoom_level: float):
        self._render_timer.start(150)
        self.status_bar.showMessage(f"Zoom: {int(zoom_level * 100)}%")

    def _on_category_toggled(self, category: str, enabled: bool):
        self._render_current_page()
        self.status_bar.showMessage(
            f"Category '{category}' {
                'enabled' if enabled else 'disabled'}")

    def _on_url_status_toggled(self, status: str, enabled: bool):
        self._render_current_page()
        self.status_bar.showMessage(
            f"URL status '{status}' {
                'enabled' if enabled else 'disabled'}")

    def _on_search_changed(self, term: str):
        self.status_bar.showMessage(
            f"{'Searching for: ' + term if term else 'Search cleared'}")

    def _update_page_metadata(self, page_number: int):
        meta: Optional[PageMetadata] = self.pdf_processor.get_page_metadata(
            page_number)
        if meta:
            annotations = meta.keywords_found + meta.urls_found
            self.keyword_panel.update_page_metadata(
                page_number, annotations, meta.content)
        else:
            self.keyword_panel.clear_metadata()

    def _refresh_annotations(self):
        self.keyword_provider.load_data()
        self.url_provider.load_data()
        self.keyword_panel.update_categories()
        self.keyword_panel.update_url_categories()
        if self.pdf_processor.document:
            self._render_current_page()

    def _on_pdf_error(self, msg: str):
        logging.error(msg)
        QMessageBox.warning(self, "PDF Error", msg)
        self.status_bar.showMessage(f"Error: {msg}")

    def show_about(self):
        QMessageBox.about(
            self,
            "About UFC PDF Document Analyzer",
            """
            <h3>UFC PDF Document Analyzer</h3>
            <p>Version 1.0.0</p>
            <ul>
                <li>PDF viewing with zoom and navigation</li>
                <li>Annotation highlighting by category</li>
                <li>Metadata analysis and statistics</li>
                <li>Customizable annotation categories</li>
            </ul>
            """
        )

    def _on_debug_step(self, step_name: str, params: Dict[str, Any]) -> None:
        """Handle debug toolbar step request."""
        try:
            self.debug_toolbar.set_status(f"Running {step_name}...")
            self.pdf_processor.execute_step(step_name, **params)
        except Exception:
            pass

    def closeEvent(self, event):
        if self.render_thread.isRunning():
            self.render_thread.stop()
        self.pdf_processor.close_document()
        event.accept()
