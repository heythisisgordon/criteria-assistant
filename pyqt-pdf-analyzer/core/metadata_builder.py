from __future__ import annotations

"""Utilities for extracting PDF page metadata."""

from dataclasses import dataclass
from typing import List, Dict
import fitz
import logging

from .annotation_system import AnnotationManager, AnnotationType
from .page_metadata import PageMetadata


@dataclass
class PageMetadataBuilder:
    """Builds :class:`PageMetadata` instances from a PyMuPDF document."""

    annotation_manager: AnnotationManager

    def build(self, document: fitz.Document, page_num: int) -> PageMetadata:
        """Extract text, bounding boxes and annotations for a page."""
        logging.debug(
            "PageMetadataBuilder.build: start extraction for page %d", page_num
        )
        page = document.load_page(page_num)
        text_content = page.get_text()
        blocks = page.get_text("dict").get("blocks", [])

        boxes: List[Dict] = []
        span_texts: List[str] = []
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    x0, y0, x1, y1 = span["bbox"]
                    boxes.append(
                        {
                            "x0": x0,
                            "y0": y0,
                            "x1": x1,
                            "y1": y1,
                            "text": span["text"],
                        }
                    )
                    span_texts.append(span["text"])

        # Batch annotation lookup for span texts
        annotations_batch = self.annotation_manager.find_annotations_batch(span_texts)
        for bbox, anns in zip(boxes, annotations_batch):
            bbox["annotations"] = anns

        # Page-level annotations
        page_annotations = self.annotation_manager.find_all_annotations_in_text(
            text_content
        )
        kws = [a for a in page_annotations if a.annotation_type == AnnotationType.KEYWORD]
        urls = [
            a
            for a in page_annotations
            if a.annotation_type == AnnotationType.URL_VALIDATION
        ]

        logging.debug(
            "PageMetadataBuilder.build: extracted %d boxes for page %d",
            len(boxes),
            page_num,
        )
        return PageMetadata(page_num, text_content, boxes, kws, urls)
