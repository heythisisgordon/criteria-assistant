"""
Main window for the PyQt PDF Document Analyzer.
"""

import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                            QMenuBar, QMenu, QStatusBar, QFileDialog, 
                            QMessageBox, QSplitter, QProgressBar, QLabel,
                            QToolBar, QApplication)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPixmap
from typing import Optional

from core.config import Config
from core.keyword_manager import KeywordManager
from core.pdf_processor import PDFProcessor, PageMetadata
from ui.pdf_viewer import PDFViewerWidget
from ui.keyword_panel import KeywordPanel

class PDFRenderThread(QThread):
    """Thread for rendering PDF pages without blocking the UI."""
    
    page_rendered = pyqtSignal(int, QPixmap)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, pdf_processor: PDFProcessor, page_number: int, zoom_level: float):
        """Initialize the render thread."""
        super().__init__()
        self.pdf_processor = pdf_processor
        self.page_number = page_number
        self.zoom_level = zoom_level
    
    def run(self):
        """Render the PDF page in a separate thread."""
        try:
            pixmap = self.pdf_processor.render_page(self.page_number, self.zoom_level)
            if pixmap:
                self.page_rendered.emit(self.page_number, pixmap)
            else:
                self.error_occurred.emit(f"Failed to render page {self.page_number + 1}")
        except Exception as e:
            self.error_occurred.emit(f"Error rendering page: {str(e)}")

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Initialize core components
        self.keyword_manager = KeywordManager()
        self.pdf_processor = PDFProcessor(self.keyword_manager)
        self.current_render_thread: Optional[PDFRenderThread] = None
        
        # UI components
        self.pdf_viewer: Optional[PDFViewerWidget] = None
        self.keyword_panel: Optional[KeywordPanel] = None
        self.status_bar: Optional[QStatusBar] = None
        self.progress_bar: Optional[QProgressBar] = None
        
        self._setup_ui()
        self._setup_connections()
        self._load_default_keywords()
        
        # Set window properties
        self.setWindowTitle("UFC PDF Document Analyzer")
        self.setMinimumSize(Config.DEFAULT_WINDOW_WIDTH, Config.DEFAULT_WINDOW_HEIGHT)
        self.resize(Config.DEFAULT_WINDOW_WIDTH, Config.DEFAULT_WINDOW_HEIGHT)
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create keyword panel
        self.keyword_panel = KeywordPanel(self.keyword_manager)
        self.keyword_panel.setMinimumWidth(300)
        self.keyword_panel.setMaximumWidth(400)
        splitter.addWidget(self.keyword_panel)
        
        # Create PDF viewer
        self.pdf_viewer = PDFViewerWidget()
        splitter.addWidget(self.pdf_viewer)
        
        # Set splitter proportions (25% for panel, 75% for viewer)
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create toolbar
        self._create_toolbar()
        
        # Create status bar
        self._create_status_bar()
    
    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Open action
        open_action = QAction("&Open PDF...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.setStatusTip("Open a PDF document")
        open_action.triggered.connect(self.open_pdf)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Load keywords action
        load_keywords_action = QAction("Load &Keywords...", self)
        load_keywords_action.setStatusTip("Load keywords from CSV file")
        load_keywords_action.triggered.connect(self.load_keywords)
        file_menu.addAction(load_keywords_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Zoom actions
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self.pdf_viewer.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self.pdf_viewer.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        fit_width_action = QAction("&Fit to Width", self)
        fit_width_action.setShortcut("Ctrl+0")
        fit_width_action.triggered.connect(self.pdf_viewer.fit_to_width)
        view_menu.addAction(fit_width_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """Create the application toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Open PDF button
        open_action = QAction("Open PDF", self)
        open_action.setStatusTip("Open a PDF document")
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # Navigation buttons (these will be connected to PDF viewer)
        prev_action = QAction("◀ Previous", self)
        prev_action.triggered.connect(self.pdf_viewer.previous_page)
        toolbar.addAction(prev_action)
        
        next_action = QAction("Next ▶", self)
        next_action.triggered.connect(self.pdf_viewer.next_page)
        toolbar.addAction(next_action)
    
    def _create_status_bar(self):
        """Create the application status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Progress bar for long operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Default status message
        self.status_bar.showMessage("Ready - Load a PDF document to begin analysis")
    
    def _setup_connections(self):
        """Set up signal connections between components."""
        # PDF viewer signals
        self.pdf_viewer.page_changed.connect(self._on_page_changed)
        self.pdf_viewer.zoom_changed.connect(self._on_zoom_changed)
        
        # Keyword panel signals
        self.keyword_panel.category_toggled.connect(self._on_category_toggled)
        self.keyword_panel.search_changed.connect(self._on_search_changed)
        self.keyword_panel.refresh_requested.connect(self._refresh_keywords)
        
        # PDF processor signals
        self.pdf_processor.error_occurred.connect(self._on_pdf_error)
    
    def _load_default_keywords(self):
        """Load default keywords on startup."""
        try:
            if self.keyword_manager.load_keywords():
                self.keyword_panel.update_categories()
                self.status_bar.showMessage("Keywords loaded successfully")
            else:
                self.status_bar.showMessage("Warning: Could not load default keywords")
        except Exception as e:
            self.status_bar.showMessage(f"Error loading keywords: {str(e)}")
    
    def open_pdf(self):
        """Open a PDF file dialog and load the selected file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF Document",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path:
            self._load_pdf(file_path)
    
    def _load_pdf(self, file_path: str):
        """
        Load a PDF file.
        
        Args:
            file_path: Path to the PDF file to load.
        """
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_bar.showMessage("Loading PDF...")
        
        # Load PDF in processor
        if self.pdf_processor.load_pdf(file_path):
            page_count = self.pdf_processor.get_page_count()
            self.pdf_viewer.set_total_pages(page_count)
            
            # Load first page
            self._render_current_page()
            
            # Update window title
            filename = os.path.basename(file_path)
            self.setWindowTitle(f"UFC PDF Document Analyzer - {filename}")
            
            self.status_bar.showMessage(f"Loaded PDF: {filename} ({page_count} pages)")
        else:
            QMessageBox.critical(
                self,
                "Error Loading PDF",
                f"Could not load PDF file:\n{file_path}"
            )
            self.status_bar.showMessage("Failed to load PDF")
        
        self.progress_bar.setVisible(False)
    
    def load_keywords(self):
        """Load keywords from a CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Keywords CSV",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            if self.keyword_manager.load_keywords(file_path):
                self.keyword_panel.update_categories()
                self.status_bar.showMessage(f"Keywords loaded from: {os.path.basename(file_path)}")
                
                # Re-render current page with new keywords
                self._render_current_page()
            else:
                QMessageBox.critical(
                    self,
                    "Error Loading Keywords",
                    f"Could not load keywords from:\n{file_path}"
                )
    
    def _render_current_page(self):
        """Render the current page with keyword highlighting."""
        if not self.pdf_processor.document:
            return
        
        current_page = self.pdf_viewer.get_current_page()
        zoom_level = self.pdf_viewer.get_zoom_level()
        
        # Cancel any existing render thread
        if self.current_render_thread and self.current_render_thread.isRunning():
            self.current_render_thread.terminate()
            self.current_render_thread.wait()
        
        # Start new render thread
        self.current_render_thread = PDFRenderThread(
            self.pdf_processor, current_page, zoom_level
        )
        self.current_render_thread.page_rendered.connect(self._on_page_rendered)
        self.current_render_thread.error_occurred.connect(self._on_pdf_error)
        self.current_render_thread.start()
        
        # Update page metadata
        self._update_page_metadata(current_page)
    
    def _on_page_rendered(self, page_number: int, pixmap: QPixmap):
        """Handle page rendering completion."""
        self.pdf_viewer.set_pixmap(pixmap, page_number)
    
    def _on_page_changed(self, page_number: int):
        """Handle page navigation."""
        self._render_current_page()
        self.status_bar.showMessage(f"Page {page_number + 1}")
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        self._render_current_page()
        self.status_bar.showMessage(f"Zoom: {int(zoom_level * 100)}%")
    
    def _on_category_toggled(self, category: str, enabled: bool):
        """Handle keyword category toggle."""
        self._render_current_page()
        action = "enabled" if enabled else "disabled"
        self.status_bar.showMessage(f"Category '{category}' {action}")
    
    def _on_search_changed(self, search_term: str):
        """Handle search term changes."""
        # For now, just update status. Could implement search highlighting later.
        if search_term:
            self.status_bar.showMessage(f"Searching for: {search_term}")
        else:
            self.status_bar.showMessage("Search cleared")
    
    def _on_pdf_error(self, error_message: str):
        """Handle PDF processing errors."""
        QMessageBox.warning(self, "PDF Error", error_message)
        self.status_bar.showMessage(f"Error: {error_message}")
    
    def _update_page_metadata(self, page_number: int):
        """Update the page metadata display."""
        metadata = self.pdf_processor.get_page_metadata(page_number)
        if metadata:
            self.keyword_panel.update_page_metadata(
                page_number,
                metadata.keywords_found,
                metadata.content
            )
        else:
            self.keyword_panel.clear_metadata()
    
    def _refresh_keywords(self):
        """Refresh keyword loading."""
        self._load_default_keywords()
        if self.pdf_processor.document:
            self._render_current_page()
    
    def show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About UFC PDF Document Analyzer",
            """
            <h3>UFC PDF Document Analyzer</h3>
            <p>Version 1.0.0</p>
            <p>A PyQt6 application for analyzing UFC/UFGS PDF documents with keyword highlighting.</p>
            <p>Features:</p>
            <ul>
            <li>PDF viewing with zoom and navigation</li>
            <li>Keyword highlighting by category</li>
            <li>Metadata analysis and statistics</li>
            <li>Customizable keyword categories</li>
            </ul>
            <p>Built with PyQt6, PyMuPDF, and Pillow.</p>
            """
        )
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Clean up resources
        if self.current_render_thread and self.current_render_thread.isRunning():
            self.current_render_thread.terminate()
            self.current_render_thread.wait()
        
        self.pdf_processor.close_document()
        event.accept()
