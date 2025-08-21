"""
Keyword panel widget for managing annotation categories and metadata display.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QLineEdit, QPushButton, QGroupBox,
    QScrollArea, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Callable, Dict, List, Tuple

from core.annotation_system import AnnotationManager, AnnotationType, Annotation
from core.keyword_provider import KeywordProvider
from core.url_provider import URLProvider
from core.config import Config

class KeywordPanel(QWidget):
    """Left panel widget for annotation management and metadata display."""

    # Signals
    category_toggled = pyqtSignal(str, bool)
    url_status_toggled = pyqtSignal(str, bool)
    search_changed = pyqtSignal(str)
    refresh_requested = pyqtSignal()

    def __init__(
        self,
        annotation_manager: AnnotationManager,
        keyword_provider: KeywordProvider,
        url_provider: URLProvider,
        parent=None
    ):
        """
        Initialize the keyword panel.

        Args:
            annotation_manager: AnnotationManager instance.
            keyword_provider: KeywordProvider instance.
            url_provider: URLProvider instance.
        """
        super().__init__(parent)
        self.annotation_manager = annotation_manager
        self.keyword_provider = keyword_provider
        self.url_provider = url_provider

        # UI state
        self.category_checkboxes: Dict[str, QCheckBox] = {}
        self.url_status_checkboxes: Dict[str, QCheckBox] = {}

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Search section
        search_group = QGroupBox("Search Annotations")
        search_layout = QVBoxLayout(search_group)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter keywords...")
        search_layout.addWidget(self.search_input)
        splitter.addWidget(search_group)

        # Keyword categories
        cat_group = QGroupBox("Keyword Categories")
        cat_layout = QVBoxLayout(cat_group)
        btn_layout = QHBoxLayout()
        self.select_all_button = QPushButton("All")
        self.select_none_button = QPushButton("None")
        btn_layout.addWidget(self.select_all_button)
        btn_layout.addWidget(self.select_none_button)
        cat_layout.addLayout(btn_layout)
        self.categories_scroll = QScrollArea()
        self.categories_scroll.setWidgetResizable(True)
        self.categories_container = QWidget()
        self.categories_layout = QVBoxLayout(self.categories_container)
        self.categories_scroll.setWidget(self.categories_container)
        cat_layout.addWidget(self.categories_scroll)
        splitter.addWidget(cat_group)

        # URL status categories
        url_group = QGroupBox("URL Status Categories")
        url_layout = QVBoxLayout(url_group)
        url_btn_layout = QHBoxLayout()
        self.select_all_url_button = QPushButton("All")
        self.select_none_url_button = QPushButton("None")
        url_btn_layout.addWidget(self.select_all_url_button)
        url_btn_layout.addWidget(self.select_none_url_button)
        url_layout.addLayout(url_btn_layout)
        self.url_scroll = QScrollArea()
        self.url_scroll.setWidgetResizable(True)
        self.url_container = QWidget()
        self.url_layout = QVBoxLayout(self.url_container)
        self.url_scroll.setWidget(self.url_container)
        url_layout.addWidget(self.url_scroll)
        splitter.addWidget(url_group)

        # Metadata display
        meta_group = QGroupBox("Page Metadata")
        meta_layout = QVBoxLayout(meta_group)
        self.metadata_text = QTextEdit()
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setFont(QFont("Courier", 8))
        meta_layout.addWidget(self.metadata_text)
        splitter.addWidget(meta_group)

        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        layout.addWidget(splitter)
        layout.addWidget(self.refresh_button)

    def _setup_connections(self):
        """Set up signal connections."""
        self.search_input.textChanged.connect(self.search_changed.emit)
        self.select_all_button.clicked.connect(lambda: self._set_all_categories(True))
        self.select_none_button.clicked.connect(lambda: self._set_all_categories(False))
        self.select_all_url_button.clicked.connect(lambda: self._set_all_urls(True))
        self.select_none_url_button.clicked.connect(lambda: self._set_all_urls(False))
        self.refresh_button.clicked.connect(self.refresh_requested.emit)

    def _populate_checkboxes(
        self,
        container: Tuple[QVBoxLayout, Dict[str, QCheckBox]],
        data: Dict[str, bool],
        color_fn: Callable[[str], str],
        toggle_fn: Callable[[str, bool], None],
    ) -> None:
        """Generic helper to populate checkbox lists."""
        layout, checkbox_map = container

        # Clear existing widgets
        for cb in checkbox_map.values():
            cb.setParent(None)
        checkbox_map.clear()

        # Populate with new data
        for label, enabled in data.items():
            cb = QCheckBox(label)
            color = color_fn(label)
            cb.setStyleSheet(f"QCheckBox::indicator:checked {{ background:{color}; }}")
            cb.setChecked(enabled)
            cb.toggled.connect(lambda checked, name=label: toggle_fn(name, checked))
            layout.addWidget(cb)
            checkbox_map[label] = cb

    def update_categories(self):
        """Populate keyword category checkboxes from the annotation framework."""
        categories = self.annotation_manager.get_all_categories()[AnnotationType.KEYWORD]
        enabled = self.keyword_provider.get_enabled_categories()
        data = {cat: cat in enabled for cat in categories}
        self._populate_checkboxes(
            (self.categories_layout, self.category_checkboxes),
            data,
            Config.get_color_for_category,
            lambda cat, checked: self.keyword_provider.set_category_enabled(cat, checked),
        )

    def update_url_categories(self):
        """Populate URL status checkboxes from the annotation framework."""
        statuses = self.annotation_manager.get_all_categories()[AnnotationType.URL_VALIDATION]
        enabled = self.url_provider.get_enabled_categories()
        data = {status: status in enabled for status in statuses}
        self._populate_checkboxes(
            (self.url_layout, self.url_status_checkboxes),
            data,
            Config.get_color_for_status,
            lambda s, checked: self.url_provider.set_category_enabled(s, checked),
        )

    def update_page_metadata(self, page_number: int, annotations: List[Annotation], content_preview: str = ""):
        """
        Display grouped annotation metadata for the current page.

        Args:
            page_number: 0-based page index.
            annotations: List of Annotation objects.
            content_preview: Optional text preview.
        """
        by_type: Dict[AnnotationType, Dict[str, List[str]]] = {}
        for ann in annotations:
            by_type.setdefault(ann.annotation_type, {}).setdefault(ann.category, []).append(ann.text)

        text = f"Page {page_number + 1}\n" + "="*20 + "\n\n"
        # Keywords
        kws = by_type.get(AnnotationType.KEYWORD, {})
        text += "Keywords:\n"
        for cat, texts in kws.items():
            text += f"  {cat}:\n"
            for t in sorted(set(texts)):
                text += f"    • {t}\n"
        text += "\n"
        # URL validations
        urls = by_type.get(AnnotationType.URL_VALIDATION, {})
        text += "URL Validations:\n"
        for cat, texts in urls.items():
            text += f"  {cat}:\n"
            for u in sorted(set(texts)):
                text += f"    • {u}\n"
        if content_preview:
            text += "\nPreview:\n" + content_preview[:200] + ("..." if len(content_preview) > 200 else "")
        self.metadata_text.setPlainText(text)

    def _set_all_categories(self, checked: bool):
        for cb in self.category_checkboxes.values():
            cb.setChecked(checked)

    def _set_all_urls(self, checked: bool):
        for cb in self.url_status_checkboxes.values():
            cb.setChecked(checked)

    def clear_metadata(self):
        """Clear metadata display."""
        self.metadata_text.setPlainText("")

    def get_search_term(self) -> str:
        """Return current search filter."""
        return self.search_input.text().strip()
