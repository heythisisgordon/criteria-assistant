"""
Keyword panel widget for managing keyword categories and search.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QCheckBox, QLineEdit, QPushButton, QGroupBox,
                            QScrollArea, QFrame, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette
from typing import Dict, List

from core.keyword_manager import KeywordManager, Keyword
from core.config import Config

class KeywordLegendWidget(QWidget):
    """Widget displaying keyword category legend with color indicators."""
    
    def __init__(self, parent=None):
        """Initialize the keyword legend widget."""
        super().__init__(parent)
        self.categories: Dict[str, str] = {}  # category -> color
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Keyword Legend")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Scroll area for legend items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(200)
        
        self.legend_widget = QWidget()
        self.legend_layout = QVBoxLayout(self.legend_widget)
        self.legend_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area.setWidget(self.legend_widget)
        layout.addWidget(self.scroll_area)
    
    def update_legend(self, categories: Dict[str, str]):
        """
        Update the legend with new categories.
        
        Args:
            categories: Dictionary mapping category names to colors.
        """
        self.categories = categories
        
        # Clear existing legend items
        for i in reversed(range(self.legend_layout.count())):
            child = self.legend_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Add new legend items
        for category, color in categories.items():
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(2, 2, 2, 2)
            
            # Color indicator
            color_label = QLabel()
            color_label.setFixedSize(16, 16)
            color_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    border: 1px solid #333;
                    border-radius: 8px;
                }}
            """)
            item_layout.addWidget(color_label)
            
            # Category name
            name_label = QLabel(category)
            name_label.setFont(QFont("Arial", 9))
            item_layout.addWidget(name_label)
            
            item_layout.addStretch()
            self.legend_layout.addWidget(item_widget)
        
        self.legend_layout.addStretch()

class KeywordPanel(QWidget):
    """Left panel widget for keyword management and metadata display."""
    
    # Signals
    category_toggled = pyqtSignal(str, bool)  # category, enabled
    search_changed = pyqtSignal(str)  # search_term
    refresh_requested = pyqtSignal()
    
    def __init__(self, keyword_manager: KeywordManager, parent=None):
        """
        Initialize the keyword panel.
        
        Args:
            keyword_manager: KeywordManager instance.
        """
        super().__init__(parent)
        self.keyword_manager = keyword_manager
        self.category_checkboxes: Dict[str, QCheckBox] = {}
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Search section
        search_group = QGroupBox("Search Keywords")
        search_layout = QVBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search keywords...")
        search_layout.addWidget(self.search_input)
        
        # Clear search button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(lambda: self.search_input.clear())
        search_layout.addWidget(clear_button)
        
        splitter.addWidget(search_group)
        
        # Categories section
        categories_group = QGroupBox("Keyword Categories")
        categories_layout = QVBoxLayout(categories_group)
        
        # Select all/none buttons
        button_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.select_none_button = QPushButton("Select None")
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.select_none_button)
        categories_layout.addLayout(button_layout)
        
        # Scroll area for category checkboxes
        self.categories_scroll = QScrollArea()
        self.categories_scroll.setWidgetResizable(True)
        self.categories_scroll.setMaximumHeight(200)
        
        self.categories_widget = QWidget()
        self.categories_layout = QVBoxLayout(self.categories_widget)
        self.categories_layout.setContentsMargins(5, 5, 5, 5)
        
        self.categories_scroll.setWidget(self.categories_widget)
        categories_layout.addWidget(self.categories_scroll)
        
        splitter.addWidget(categories_group)
        
        # Legend section
        self.legend_widget = KeywordLegendWidget()
        splitter.addWidget(self.legend_widget)
        
        # Statistics section
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_label = QLabel("No keywords loaded")
        self.stats_label.setWordWrap(True)
        self.stats_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.stats_label)
        
        splitter.addWidget(stats_group)
        
        # Metadata section
        metadata_group = QGroupBox("Page Metadata")
        metadata_layout = QVBoxLayout(metadata_group)
        
        self.metadata_text = QTextEdit()
        self.metadata_text.setMaximumHeight(150)
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setFont(QFont("Courier", 8))
        metadata_layout.addWidget(self.metadata_text)
        
        splitter.addWidget(metadata_group)
        
        # Set splitter proportions
        splitter.setSizes([100, 150, 100, 80, 120])
        
        layout.addWidget(splitter)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Keywords")
        layout.addWidget(self.refresh_button)
    
    def _setup_connections(self):
        """Set up signal connections."""
        self.search_input.textChanged.connect(self.search_changed.emit)
        self.select_all_button.clicked.connect(self._select_all_categories)
        self.select_none_button.clicked.connect(self._select_no_categories)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
    
    def update_categories(self):
        """Update the category checkboxes based on loaded keywords."""
        # Clear existing checkboxes
        for checkbox in self.category_checkboxes.values():
            checkbox.setParent(None)
        self.category_checkboxes.clear()
        
        # Add checkboxes for each category
        categories = self.keyword_manager.get_categories()
        legend_data = {}
        
        for category in categories:
            # Create checkbox
            checkbox = QCheckBox(category)
            checkbox.setChecked(self.keyword_manager.is_category_enabled(category))
            
            # Get color for this category
            keywords = self.keyword_manager.get_keywords_for_category(category)
            color = keywords[0].color if keywords else "#808080"
            
            # Style checkbox with category color
            checkbox.setStyleSheet(f"""
                QCheckBox::indicator:checked {{
                    background-color: {color};
                    border: 2px solid #333;
                }}
                QCheckBox::indicator:unchecked {{
                    background-color: white;
                    border: 2px solid {color};
                }}
            """)
            
            # Connect signal
            checkbox.toggled.connect(
                lambda checked, cat=category: self._on_category_toggled(cat, checked)
            )
            
            self.categories_layout.addWidget(checkbox)
            self.category_checkboxes[category] = checkbox
            legend_data[category] = color
        
        # Update legend
        self.legend_widget.update_legend(legend_data)
        
        # Update statistics
        self._update_statistics()
    
    def _on_category_toggled(self, category: str, checked: bool):
        """Handle category checkbox toggle."""
        self.keyword_manager.enable_category(category, checked)
        self.category_toggled.emit(category, checked)
        self._update_statistics()
    
    def _select_all_categories(self):
        """Select all category checkboxes."""
        for checkbox in self.category_checkboxes.values():
            checkbox.setChecked(True)
    
    def _select_no_categories(self):
        """Deselect all category checkboxes."""
        for checkbox in self.category_checkboxes.values():
            checkbox.setChecked(False)
    
    def _update_statistics(self):
        """Update the statistics display."""
        stats = self.keyword_manager.get_keyword_stats()
        
        if not stats:
            self.stats_label.setText("No keywords loaded")
            return
        
        total_keywords = sum(stats.values())
        enabled_categories = len(self.keyword_manager.enabled_categories)
        total_categories = len(stats)
        
        stats_text = f"Total Keywords: {total_keywords}\n"
        stats_text += f"Categories: {enabled_categories}/{total_categories} enabled\n\n"
        
        for category, count in sorted(stats.items()):
            enabled = "✓" if self.keyword_manager.is_category_enabled(category) else "✗"
            stats_text += f"{enabled} {category}: {count}\n"
        
        self.stats_label.setText(stats_text)
    
    def update_page_metadata(self, page_number: int, keywords_found: List[Keyword], content_preview: str = ""):
        """
        Update the page metadata display.
        
        Args:
            page_number: Current page number.
            keywords_found: List of keywords found on the page.
            content_preview: Preview of page content.
        """
        metadata_text = f"Page {page_number + 1} Analysis\n"
        metadata_text += "=" * 20 + "\n\n"
        
        if keywords_found:
            metadata_text += f"Keywords Found: {len(keywords_found)}\n\n"
            
            # Group keywords by category
            by_category = {}
            for keyword in keywords_found:
                if keyword.category not in by_category:
                    by_category[keyword.category] = []
                by_category[keyword.category].append(keyword.text)
            
            for category, keywords in by_category.items():
                metadata_text += f"{category}:\n"
                for keyword in sorted(set(keywords)):  # Remove duplicates and sort
                    metadata_text += f"  • {keyword}\n"
                metadata_text += "\n"
        else:
            metadata_text += "No keywords found on this page.\n\n"
        
        if content_preview:
            metadata_text += "Content Preview:\n"
            metadata_text += "-" * 15 + "\n"
            # Show first 200 characters of content
            preview = content_preview[:200].strip()
            if len(content_preview) > 200:
                preview += "..."
            metadata_text += preview
        
        self.metadata_text.setPlainText(metadata_text)
    
    def clear_metadata(self):
        """Clear the metadata display."""
        self.metadata_text.setPlainText("No page selected")
    
    def get_search_term(self) -> str:
        """Get the current search term."""
        return self.search_input.text().strip()
