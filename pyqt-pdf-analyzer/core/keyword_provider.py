import pandas as pd
from typing import List, Set, Dict
from core.annotation_system import AnnotationProvider, Annotation, AnnotationType
from core.config import Config

class KeywordProvider(AnnotationProvider):
    """Provides keyword-based annotations."""
    
    def __init__(self):
        self.keywords_df: pd.DataFrame = pd.DataFrame()
        self.enabled_categories: Set[str] = set()
        self._keyword_lookup: Dict[str, List[Annotation]] = {}
    
    def load_data(self, source_path: str = None) -> bool:
        """Load keywords from CSV file."""
        if source_path is None:
            source_path = Config.get_keywords_path()
        try:
            self.keywords_df = pd.read_csv(source_path)
            required_cols = ['keyword', 'category', 'color']
            if not all(col in self.keywords_df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            self._build_keyword_lookup()
            self.enabled_categories = set(self.keywords_df['category'].unique())
            return True
        except Exception as e:
            print(f"Error loading keywords: {e}")
            return False
    
    def _build_keyword_lookup(self):
        """Build lookup of keyword text to Annotation instances."""
        self._keyword_lookup.clear()
        for _, row in self.keywords_df.iterrows():
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
    
    def get_categories(self) -> Set[str]:
        """Get all keyword categories."""
        return set(self.keywords_df['category'].unique()) if not self.keywords_df.empty else set()
    
    def get_enabled_categories(self) -> Set[str]:
        """Get enabled keyword categories."""
        return self.enabled_categories.copy()
    
    def set_category_enabled(self, category: str, enabled: bool):
        """Enable or disable a keyword category."""
        if enabled:
            self.enabled_categories.add(category)
        else:
            self.enabled_categories.discard(category)
