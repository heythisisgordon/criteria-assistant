import logging
from typing import List, Dict

from core.annotation_system import Annotation, AnnotationType
from core.base_csv_provider import BaseCSVAnnotationProvider
from core.config import Config

logger = logging.getLogger(__name__)

class KeywordProvider(BaseCSVAnnotationProvider):
    """Provides keyword-based annotations."""

    required_columns = ["keyword", "category", "color"]
    category_column = "category"

    def __init__(self):
        super().__init__()
        self._keyword_lookup: Dict[str, List[Annotation]] = {}

    def get_default_source_path(self) -> str:
        return Config.get_keywords_path()

    def _post_load(self) -> None:
        self._build_keyword_lookup()
    
    def _build_keyword_lookup(self):
        """Build lookup of keyword text to Annotation instances."""
        self._keyword_lookup.clear()
        for _, row in self.data_df.iterrows():
            text = str(row['keyword']).lower()
            annotation = Annotation(
                text=text,
                annotation_type=AnnotationType.KEYWORD,
                category=str(row['category']),
                color=str(row['color']),
                metadata={'original_text': str(row['keyword'])}
            )
            self._keyword_lookup.setdefault(text, []).append(annotation)
    
    def find_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find keyword annotations in the given text."""
        found: List[Annotation] = []
        if not text:
            return found
        text_lower = text.lower()
        for keyword, annotations in self._keyword_lookup.items():
            if keyword in text_lower:
                for ann in annotations:
                    if ann.category in self.enabled_categories:
                        found.append(ann)
        return found
    
