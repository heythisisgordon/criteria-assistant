"""
Main window for the PyQt PDF Document Analyzer.
"""

import logging
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QMenuBar, QMenu, QStatusBar, QFileDialog,
    QMessageBox, QSplitter, QProgressBar, QLabel,
    QToolBar, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QImage
from typing import Optional

from core.config import Config
from core.keyword_provider import KeywordProvider
from core.url_provider import URLProvider
from core.annotation_system import AnnotationManager, AnnotationType
from core.pdf_processor import PDFProcessor, PageMetadata
from ui.pdf_viewer import PDFViewerWidget
from ui.keyword_panel import KeywordPanel

class PDFRenderThread(QThread):
    """Thread for rendering PDF pages without blocking the UI."""
    page_rendered = pyqtSignal(QImage, int)
    error_occurred = pyqtSignal(str)

    def __init__(self, pdf_processor: PDFProcessor, page_number: int, zoom_level: float):
        super().__init__()
        self.pdf_processor = pdf_processor
        self.page_number = page_number
        self.zoom_level = zoom_level

    def run(self):
        try:
            image = self.pdf_processor.render_page(self.page_number, self.zoom_level)
            if image:
                self.page_rendered.emit(image, self.page_number)
            else:
                self.error_occurred.emit(f"Failed to render page {self.page_number + 1}")
        except Exception as e:
            logging.exception("Error rendering page")
            self.error_occurred.emit(f"Error rendering page: {str(e)}")

class MainWindow(QMainWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()
        # Initialize annotation framework
        self.annotation_manager = AnnotationManager()
        self.keyword_provider = KeywordProvider()
        self.url_provider = URLProvider()
        # Register providers
        self.annotation_manager.register_provider(AnnotationType.KEYWORD, self.keyword_provider)
        self.annotation_manager.register_provider(AnnotationType.URL_VALIDATION, self.url_provider)
        # Register renderers inside PDFProcessor
        self.pdf_processor = PDFProcessor(self.annotation_manager)
        self.current_render_thread: Optional[PDFRenderThread] = None

        # UI components
        self.pdf_viewer: Optional[PDFViewerWidget] = None
        self.keyword_panel: Optional[KeywordPanel] = None
        self.status_bar: Optional[QStatusBar] = None
        self.progress_bar: Optional[QProgressBar] = None

        self._setup_ui()
        self._setup_connections()

        # Load default data
        self.keyword_provider.load_data()
        self.url_provider.load_data()
        self.keyword_panel.update_categories()
        self.keyword_panel.update_url_categories()

        self.setWindowTitle("UFC PDF Document Analyzer")
        self.setMinimumSize(Config.DEFAULT_WINDOW_WIDTH, Config.DEFAULT_WINDOW_HEIGHT)
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
        view_menu.addAction(QAction("Zoom &In", self, triggered=self.pdf_viewer.zoom_in))
        view_menu.addAction(QAction("Zoom &Out", self, triggered=self.pdf_viewer.zoom_out))
        view_menu.addAction(QAction("&Fit to Width", self, triggered=self.pdf_viewer.fit_to_width))
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self, triggered=self.show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        toolbar.addAction(QAction("Open PDF", self, triggered=self.open_pdf))
        toolbar.addSeparator()
        toolbar.addAction(QAction("◀ Previous", self, triggered=self.pdf_viewer.previous_page))
        toolbar.addAction(QAction("Next ▶", self, triggered=self.pdf_viewer.next_page))

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage("Ready - Load a PDF document to begin analysis")

    def _setup_connections(self):
        self.pdf_viewer.page_changed.connect(self._on_page_changed)
        self.pdf_viewer.zoom_changed.connect(self._on_zoom_changed)
        self.keyword_panel.category_toggled.connect(self._on_category_toggled)
        self.keyword_panel.url_status_toggled.connect(self._on_url_status_toggled)
        self.keyword_panel.search_changed.connect(self._on_search_changed)
        self.keyword_panel.refresh_requested.connect(self._refresh_annotations)
        self.pdf_processor.error_occurred.connect(self._on_pdf_error)

    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF Document", "", "PDF Files (*.pdf);;All Files (*)")
        if path:
            self._load_pdf(path)

    def _load_pdf(self, file_path: str):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage("Loading PDF...")
        if self.pdf_processor.load_pdf(file_path):
            count = self.pdf_processor.get_page_count()
            self.pdf_viewer.set_total_pages(count)
            self._render_current_page()
            self.setWindowTitle(f"UFC PDF Document Analyzer - {os.path.basename(file_path)}")
            self.status_bar.showMessage(f"Loaded PDF: {os.path.basename(file_path)} ({count} pages)")
        else:
            QMessageBox.critical(self, "Error Loading PDF", f"Could not load PDF:\n{file_path}")
            self.status_bar.showMessage("Failed to load PDF")
        self.progress_bar.setVisible(False)

    def load_keywords(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Keywords CSV", "", "CSV Files (*.csv);;All Files (*)")
        if path and self.keyword_provider.load_data(path):
            self.keyword_panel.update_categories()
            self.status_bar.showMessage(f"Keywords loaded from: {os.path.basename(path)}")
            self._render_current_page()

    def load_url_validations(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load URL Validations CSV", "", "CSV Files (*.csv);;All Files (*)")
        if path and self.url_provider.load_data(path):
            self.keyword_panel.update_url_categories()
            self.status_bar.showMessage(f"URL validations loaded from: {os.path.basename(path)}")
            self._render_current_page()

    def _render_current_page(self):
        if not self.pdf_processor.document:
            return
        page = self.pdf_viewer.get_current_page()
        zoom = self.pdf_viewer.get_zoom_level()
        if self.current_render_thread and self.current_render_thread.isRunning():
            self.current_render_thread.terminate()
            self.current_render_thread.wait()
        self.current_render_thread = PDFRenderThread(self.pdf_processor, page, zoom)
        self.current_render_thread.page_rendered.connect(self.pdf_viewer.set_pixmap)
        self.current_render_thread.error_occurred.connect(self._on_pdf_error)
        self.current_render_thread.start()
        self._update_page_metadata(page)

    def _on_page_changed(self, page_number: int):
        self._render_current_page()
        self.status_bar.showMessage(f"Page {page_number + 1}")

    def _on_zoom_changed(self, zoom_level: float):
        self._render_current_page()
        self.status_bar.showMessage(f"Zoom: {int(zoom_level * 100)}%")

    def _on_category_toggled(self, category: str, enabled: bool):
        self._render_current_page()
        self.status_bar.showMessage(f"Category '{category}' {'enabled' if enabled else 'disabled'}")

    def _on_url_status_toggled(self, status: str, enabled: bool):
        self._render_current_page()
        self.status_bar.showMessage(f"URL status '{status}' {'enabled' if enabled else 'disabled'}")

    def _on_search_changed(self, term: str):
        self.status_bar.showMessage(f"{'Searching for: ' + term if term else 'Search cleared'}")

    def _update_page_metadata(self, page_number: int):
        meta: Optional[PageMetadata] = self.pdf_processor.get_page_metadata(page_number)
        if meta:
            annotations = meta.keywords_found + meta.urls_found
            self.keyword_panel.update_page_metadata(page_number, annotations, meta.content)
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

    def closeEvent(self, event):
        if self.current_render_thread and self.current_render_thread.isRunning():
            self.current_render_thread.terminate()
            self.current_render_thread.wait()
        self.pdf_processor.close_document()
        event.accept()
