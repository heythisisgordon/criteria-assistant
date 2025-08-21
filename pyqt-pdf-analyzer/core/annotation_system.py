from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Set, Any, Optional
from threading import RLock
from collections import OrderedDict
import hashlib
import logging
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
    """Central manager for all annotation types with a size-bounded cache.

    The cache stores recently computed annotations keyed by a hash of the
    input text. Access to the cache is protected by a re-entrant lock. The
    cache is cleared whenever providers are updated via :meth:`register_provider`.
    """

    def __init__(self):
        self.providers: Dict[AnnotationType, AnnotationProvider] = {}
        self.renderers: Dict[AnnotationType, AnnotationRenderer] = {}
        self._cache_lock = RLock()
        self._cache: "OrderedDict[str, List[Annotation]]" = OrderedDict()
        self._cache_size = Config.ANNOTATION_CACHE_SIZE

    def _get_cache_key(self, text: str) -> str:
        """Generate a fixed-size cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()

    def register_provider(self, annotation_type: AnnotationType, provider: AnnotationProvider):
        """Register an annotation provider and clear cache.

        Updating providers invalidates the cache to ensure annotations are
        recomputed using the latest provider data.
        """
        self.providers[annotation_type] = provider
        self._clear_cache()

    def register_renderer(self, annotation_type: AnnotationType, renderer: AnnotationRenderer):
        """Register an annotation renderer."""
        self.renderers[annotation_type] = renderer

    def find_all_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find all annotations with explicit, thread-safe caching."""
        key = self._get_cache_key(text)
        logging.debug(
            f"AnnotationManager.find_all_annotations_in_text: key={key[:8]}..., text_len={len(text)}"
        )
        cached = self._get_cached_annotations(key)
        if cached is not None:
            return cached
        annotations = self._compute_annotations(text)
        self._set_cached_annotations(key, annotations)
        return annotations

    def _compute_annotations(self, text: str) -> List[Annotation]:
        """Compute annotations for the given text without caching."""
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

    def _get_cached_annotations(self, key: str) -> Optional[List[Annotation]]:
        """Retrieve annotations from the cache if available."""
        with self._cache_lock:
            annotations = self._cache.get(key)
            if annotations is not None:
                self._cache.move_to_end(key)
            return annotations

    def _set_cached_annotations(self, key: str, annotations: List[Annotation]):
        """Store annotations in the cache and enforce size limit."""
        with self._cache_lock:
            self._cache[key] = annotations
            self._cache.move_to_end(key)
            if len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)

    def _clear_cache(self):
        """Clear annotation cache when providers change."""
        with self._cache_lock:
            self._cache.clear()
