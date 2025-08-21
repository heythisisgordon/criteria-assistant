from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Set, Any
from PyQt6.QtCore import QMutex, QMutexLocker
import hashlib

class AnnotationType(Enum):
    KEYWORD = "keyword"
    URL_VALIDATION = "url_validation"
    REFERENCE = "reference"  # Future
    ERROR = "error"          # Future

@dataclass
class Annotation:
    """Base annotation data structure."""
    text: str
    annotation_type: AnnotationType
    category: str
    color: str
    metadata: Dict[str, Any]
    enabled: bool = True

    def __post_init__(self):
        """Validate annotation data."""
        if not self.text or not self.category:
            raise ValueError("Annotation must have text and category")

class AnnotationProvider(ABC):
    """Abstract base for annotation data providers."""

    @abstractmethod
    def load_data(self, source_path: str = None) -> bool:
        """Load annotation data from source."""
        pass

    @abstractmethod
    def find_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find all annotations in the given text."""
        pass

    @abstractmethod
    def get_categories(self) -> Set[str]:
        """Get all available categories."""
        pass

    @abstractmethod
    def get_enabled_categories(self) -> Set[str]:
        """Get currently enabled categories."""
        pass

    @abstractmethod
    def set_category_enabled(self, category: str, enabled: bool):
        """Enable or disable a category."""
        pass

class AnnotationRenderer(ABC):
    """Abstract base for annotation rendering."""

    @abstractmethod
    def render_annotation(self, annotation: Annotation, draw_context: Any, bounds: Dict[str, int]):
        """Render a single annotation."""
        pass

    @abstractmethod
    def get_render_priority(self) -> int:
        """Get rendering priority (lower = background, higher = foreground)."""
        pass

class AnnotationManager:
    """Central manager for all annotation types."""

    def __init__(self):
        self.providers: Dict[AnnotationType, AnnotationProvider] = {}
        self.renderers: Dict[AnnotationType, AnnotationRenderer] = {}
        self._annotation_cache: Dict[str, List[Annotation]] = {}
        self._cache_mutex = QMutex()

    def _get_cache_key(self, text: str) -> str:
        """Generate a fixed-size cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()

    def register_provider(self, annotation_type: AnnotationType, provider: AnnotationProvider):
        """Register an annotation provider."""
        self.providers[annotation_type] = provider
        self._clear_cache()

    def register_renderer(self, annotation_type: AnnotationType, renderer: AnnotationRenderer):
        """Register an annotation renderer."""
        self.renderers[annotation_type] = renderer

    def find_all_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find all annotations from all providers."""
        key = self._get_cache_key(text)
        with QMutexLocker(self._cache_mutex):
            if key in self._annotation_cache:
                return self._annotation_cache[key]

            all_annotations: List[Annotation] = []
            for provider in self.providers.values():
                anns = provider.find_annotations_in_text(text)
                all_annotations.extend(anns)

            # Sort by render priority
            all_annotations.sort(key=lambda a: self.renderers[a.annotation_type].get_render_priority())
            self._annotation_cache[key] = all_annotations
            return all_annotations

    def render_annotations(self, annotations: List[Annotation], draw_context: Any, bounds: Dict[str, int]):
        """Render all annotations in priority order."""
        for annotation in annotations:
            if annotation.enabled:
                renderer = self.renderers.get(annotation.annotation_type)
                if renderer:
                    renderer.render_annotation(annotation, draw_context, bounds)

    def get_all_categories(self) -> Dict[AnnotationType, Set[str]]:
        """Get categories from all providers."""
        return {
            ann_type: provider.get_categories()
            for ann_type, provider in self.providers.items()
        }

    def _clear_cache(self):
        """Clear annotation cache when providers change."""
        self._annotation_cache.clear()
