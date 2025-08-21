import logging
import re
from typing import List, Dict

from core.annotation_system import Annotation, AnnotationType
from core.base_csv_provider import BaseCSVAnnotationProvider
from core.config import Config
from core.url_utils import COMPILED_URL_PATTERNS

logger = logging.getLogger(__name__)

class URLProvider(BaseCSVAnnotationProvider):
    """Provides URL validation annotations."""

    required_columns = [
        "url",
        "status",
        "response_code",
        "final_url",
        "is_wbdg",
        "check_certainty",
    ]
    category_column = "status"

    def __init__(self):
        super().__init__()
        self._url_lookup: Dict[str, Annotation] = {}
        self.compiled_patterns = COMPILED_URL_PATTERNS

    def get_default_source_path(self) -> str:
        return Config.get_url_validation_path()

    def _post_load(self) -> None:
        self._build_lookup()
    
    def _build_lookup(self):
        """Build lookup of URL text to Annotation."""
        self._url_lookup.clear()
        for _, row in self.data_df.iterrows():
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
    
