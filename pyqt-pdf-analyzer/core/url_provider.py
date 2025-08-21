import pandas as pd
import re
from typing import List, Set, Dict
from core.annotation_system import AnnotationProvider, Annotation, AnnotationType
from core.config import Config

class URLProvider(AnnotationProvider):
    """Provides URL validation annotations."""
    
    def __init__(self):
        self.validations_df: pd.DataFrame = pd.DataFrame()
        self.enabled_categories: Set[str] = set()
        self._url_lookup: Dict[str, Annotation] = {}
        # Detection patterns
        self.url_patterns = [
            r'https?://[^\s<>"{}|\\^`\\[\\]]+',
            r'www\.[^\s<>"{}|\\^`\\[\\]]+',
            r'[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\\[\\]]*)?',
            r'mailto:[^\s<>"{}|\\^`\\[\\]]+'
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.url_patterns]
    
    def load_data(self, source_path: str = None) -> bool:
        """Load URL validation data from CSV."""
        if source_path is None:
            source_path = Config.get_url_validation_path()
        try:
            self.validations_df = pd.read_csv(source_path)
            required_cols = ['url', 'status', 'response_code', 'final_url', 'is_wbdg', 'check_certainty']
            if not all(col in self.validations_df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            self._build_lookup()
            self.enabled_categories = set(self.validations_df['status'].unique())
            return True
        except Exception as e:
            print(f"Error loading URL validations: {e}")
            return False
    
    def _build_lookup(self):
        """Build lookup of URL text to Annotation."""
        self._url_lookup.clear()
        for _, row in self.validations_df.iterrows():
            url_text = str(row['url'])
            ann = Annotation(
                text=url_text,
                annotation_type=AnnotationType.URL_VALIDATION,
                category=str(row['status']),
                color=Config.get_color_for_status(str(row['status'])),
                metadata={
                    'response_code': row.get('response_code'),
                    'final_url': str(row['final_url']),
                    'error_message': row.get('error_message'),
                    'is_wbdg': bool(row['is_wbdg']),
                    'check_certainty': str(row['check_certainty'])
                }
            )
            self._url_lookup[url_text] = ann
    
    def find_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find URL annotations in the given text."""
        found: List[Annotation] = []
        if not text:
            return found
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                candidate = match.group().strip()
                # Clean tags and punctuation
                candidate = re.sub(r'<[^>]+>', '', candidate).rstrip('.,;:!?')
                ann = self._url_lookup.get(candidate)
                if ann and ann.category in self.enabled_categories:
                    found.append(ann)
        return found
    
    def get_categories(self) -> Set[str]:
        """Get all URL status categories."""
        return set(self.validations_df['status'].unique()) if not self.validations_df.empty else set()
    
    def get_enabled_categories(self) -> Set[str]:
        """Get enabled URL status categories."""
        return self.enabled_categories.copy()
    
    def set_category_enabled(self, category: str, enabled: bool):
        """Enable or disable a URL status category."""
        if enabled:
            self.enabled_categories.add(category)
        else:
            self.enabled_categories.discard(category)
