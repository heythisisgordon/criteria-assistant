"""
PDF viewer widget with zoom and navigation capabilities.
"""

from PyQt6.QtWidgets import (QWidget, QScrollArea, QLabel, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QSlider, QSpinBox,
                            QSizePolicy, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QPainter, QFont, QImage
from typing import Optional

from core.config import Config

class PDFViewerWidget(QScrollArea):
    """Custom PDF viewer widget with zoom and scroll capabilities."""
    
    # Signals
    page_changed = pyqtSignal(int)  # page_number
    zoom_changed = pyqtSignal(float)  # zoom_level
    
    def __init__(self, parent=None):
        """Initialize the PDF viewer widget."""
        super().__init__(parent)
        
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = Config.DEFAULT_ZOOM_LEVEL
        self.current_pixmap: Optional[QPixmap] = None
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Configure scroll area
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create navigation controls
        nav_layout = QHBoxLayout()
        
        # Previous page button
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.setEnabled(False)
        nav_layout.addWidget(self.prev_button)
        
        # Page info
        self.page_label = QLabel("Page 0 of 0")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.page_label)
        
        # Next page button
        self.next_button = QPushButton("Next ▶")
        self.next_button.setEnabled(False)
        nav_layout.addWidget(self.next_button)
        
        nav_layout.addStretch()
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        
        # Zoom out button
        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.setFixedSize(30, 30)
        zoom_layout.addWidget(self.zoom_out_button)
        
        # Zoom slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(int(Config.MIN_ZOOM * 100))
        self.zoom_slider.setMaximum(int(Config.MAX_ZOOM * 100))
        self.zoom_slider.setValue(int(Config.DEFAULT_ZOOM_LEVEL * 100))
        self.zoom_slider.setFixedWidth(150)
        zoom_layout.addWidget(self.zoom_slider)
        
        # Zoom in button
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setFixedSize(30, 30)
        zoom_layout.addWidget(self.zoom_in_button)
        
        # Zoom percentage label
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        zoom_layout.addWidget(self.zoom_label)
        
        # Fit to width button
        self.fit_width_button = QPushButton("Fit Width")
        zoom_layout.addWidget(self.fit_width_button)
        
        nav_layout.addLayout(zoom_layout)
        main_layout.addLayout(nav_layout)
        
        # PDF display area
        self.pdf_label = QLabel()
        self.pdf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf_label.setStyleSheet("QLabel { background-color: white; border: 1px solid #ccc; }")
        self.pdf_label.setMinimumSize(400, 500)
        self.pdf_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Set placeholder text
        self.pdf_label.setText("No PDF loaded\n\nUse File → Open to load a PDF document")
        self.pdf_label.setWordWrap(True)
        
        main_layout.addWidget(self.pdf_label)
        
        self.setWidget(main_widget)
    
    def _setup_connections(self):
        """Set up signal connections."""
        self.prev_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        self.fit_width_button.clicked.connect(self.fit_to_width)
    
    def set_pixmap(self, image: QImage, page_number: int):
        """
        Set the rendered page image.

        Args:
            image: QImage to display.
            page_number: Current page number (0-based).
        """
        self.current_pixmap = QPixmap.fromImage(image) if image else None
        self.current_page = page_number

        if self.current_pixmap:
            # Scale pixmap according to zoom level
            scaled_pixmap = self.current_pixmap.scaled(
                self.current_pixmap.size() * self.zoom_level,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.pdf_label.setPixmap(scaled_pixmap)
        else:
            self.pdf_label.clear()
            self.pdf_label.setText("Error loading page")
        
        self._update_page_info()
        self._update_navigation_buttons()
    
    def set_total_pages(self, total_pages: int):
        """Set the total number of pages."""
        self.total_pages = total_pages
        self._update_page_info()
        self._update_navigation_buttons()
    
    def previous_page(self):
        """Navigate to the previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.page_changed.emit(self.current_page)
            self._update_page_info()
            self._update_navigation_buttons()
    
    def next_page(self):
        """Navigate to the next page."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.page_changed.emit(self.current_page)
            self._update_page_info()
            self._update_navigation_buttons()
    
    def go_to_page(self, page_number: int):
        """
        Navigate to a specific page.
        
        Args:
            page_number: Page number to navigate to (0-based).
        """
        if 0 <= page_number < self.total_pages:
            self.current_page = page_number
            self.page_changed.emit(self.current_page)
            self._update_page_info()
            self._update_navigation_buttons()
    
    def zoom_in(self):
        """Increase zoom level."""
        new_zoom = min(Config.MAX_ZOOM, self.zoom_level + Config.ZOOM_STEP)
        self.set_zoom_level(new_zoom)
    
    def zoom_out(self):
        """Decrease zoom level."""
        new_zoom = max(Config.MIN_ZOOM, self.zoom_level - Config.ZOOM_STEP)
        self.set_zoom_level(new_zoom)
    
    def set_zoom_level(self, zoom_level: float):
        """
        Set the zoom level.
        
        Args:
            zoom_level: New zoom level.
        """
        zoom_level = max(Config.MIN_ZOOM, min(Config.MAX_ZOOM, zoom_level))
        
        if abs(zoom_level - self.zoom_level) > 0.01:  # Avoid unnecessary updates
            self.zoom_level = zoom_level
            
            # Update slider without triggering signal
            self.zoom_slider.blockSignals(True)
            self.zoom_slider.setValue(int(zoom_level * 100))
            self.zoom_slider.blockSignals(False)
            
            # Update zoom label
            self.zoom_label.setText(f"{int(zoom_level * 100)}%")
            
            # Re-render current page with new zoom
            if self.current_pixmap:
                scaled_pixmap = self.current_pixmap.scaled(
                    self.current_pixmap.size() * zoom_level,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.pdf_label.setPixmap(scaled_pixmap)
            
            self.zoom_changed.emit(zoom_level)
    
    def fit_to_width(self):
        """Fit the PDF to the width of the viewer."""
        if not self.current_pixmap:
            return
            
        # Calculate zoom level to fit width
        viewer_width = self.viewport().width() - 40  # Account for margins
        pixmap_width = self.current_pixmap.width()
        
        if pixmap_width > 0:
            zoom_level = viewer_width / pixmap_width
            zoom_level = max(Config.MIN_ZOOM, min(Config.MAX_ZOOM, zoom_level))
            self.set_zoom_level(zoom_level)
    
    def _on_zoom_slider_changed(self, value: int):
        """Handle zoom slider value changes."""
        zoom_level = value / 100.0
        self.set_zoom_level(zoom_level)
    
    def _update_page_info(self):
        """Update the page information display."""
        if self.total_pages > 0:
            self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        else:
            self.page_label.setText("Page 0 of 0")
    
    def _update_navigation_buttons(self):
        """Update the state of navigation buttons."""
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < self.total_pages - 1)
    
    def clear(self):
        """Clear the PDF display."""
        self.pdf_label.clear()
        self.pdf_label.setText("No PDF loaded\n\nUse File → Open to load a PDF document")
        self.current_pixmap = None
        self.current_page = 0
        self.total_pages = 0
        self._update_page_info()
        self._update_navigation_buttons()
    
    def get_current_page(self) -> int:
        """Get the current page number (0-based)."""
        return self.current_page
    
    def get_zoom_level(self) -> float:
        """Get the current zoom level."""
        return self.zoom_level
