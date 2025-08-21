from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Set, Any
from PyQt6.QtCore import QMutex, QMutexLocker
import hashlib
import logging
from functools import lru_cache
from core.config import Config

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
    """Central manager for all annotation types with bounded LRU cache."""

    def __init__(self):
        self.providers: Dict[AnnotationType, AnnotationProvider] = {}
        self.renderers: Dict[AnnotationType, AnnotationRenderer] = {}
        self._cache_mutex = QMutex()
        # Bounded LRU cache: decorated method taking (key, text)
        self.find_annotations_cached = lru_cache(maxsize=Config.ANNOTATION_CACHE_SIZE)(
            self._find_annotations_impl
        )

    def _get_cache_key(self, text: str) -> str:
        """Generate a fixed-size cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()

    def register_provider(self, annotation_type: AnnotationType, provider: AnnotationProvider):
        """Register an annotation provider and clear cache."""
        self.providers[annotation_type] = provider
        self._clear_cache()

    def register_renderer(self, annotation_type: AnnotationType, renderer: AnnotationRenderer):
        """Register an annotation renderer."""
        self.renderers[annotation_type] = renderer

    def find_all_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find all annotations using a bounded LRU cache."""
        key = self._get_cache_key(text)
        logging.debug(f"AnnotationManager.find_all_annotations_in_text: key={key[:8]}..., text_len={len(text)}")
        with QMutexLocker(self._cache_mutex):
            return self.find_annotations_cached(key, text)

    def find_annotations_batch(self, texts: List[str]) -> List[List[Annotation]]:
        """Find annotations for a batch of texts with a single lock acquisition."""
        keys = [self._get_cache_key(t) for t in texts]
        logging.debug(
            "AnnotationManager.find_annotations_batch: batch_size=%d", len(texts)
        )
        with QMutexLocker(self._cache_mutex):
            return [self.find_annotations_cached(k, t) for k, t in zip(keys, texts)]

    def _find_annotations_impl(self, key: str, text: str) -> List[Annotation]:
        """Implementation for computing annotations for given text."""
        all_annotations: List[Annotation] = []
        for provider in self.providers.values():
            anns = provider.find_annotations_in_text(text)
            all_annotations.extend(anns)
        # Sort by render priority
        all_annotations.sort(key=lambda a: self.renderers[a.annotation_type].get_render_priority())
        logging.debug(f"AnnotationManager._find_annotations_impl: computed {len(all_annotations)} annotations")
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
        self.find_annotations_cached.cache_clear()
