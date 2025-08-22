from dataclasses import dataclass
from typing import Dict
from core.page_metadata import PageMetadata

@dataclass
class DocumentInfo:
    """
    Document-level metadata including page-specific metadata.
    """
    page_count: int                  # Total number of pages in the document
    title: str                       # PDF metadata title
    author: str                      # PDF metadata author
    subject: str                     # PDF metadata subject
    file_path: str                   # Path to the opened PDF file
    page_metadata: Dict[int, PageMetadata]  
    # Mapping from page index to PageMetadata (bounding boxes, text, annotations)
