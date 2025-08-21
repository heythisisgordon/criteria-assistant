from dataclasses import dataclass
from typing import List, Dict

from .annotation_system import Annotation


@dataclass
class PageMetadata:
    """Metadata for a single PDF page."""

    page_number: int
    content: str
    bounding_boxes: List[Dict]
    keywords_found: List[Annotation]
    urls_found: List[Annotation]

