"""
PDF processing and highlighting functionality.
Handles PDF loading, rendering, and keyword highlighting.
"""

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker
import io
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from core.annotation_system import AnnotationManager, AnnotationType, Annotation
from core.config import Config

@dataclass
class PageMetadata:
    """Metadata for a single PDF page."""
    page_number: int
    content: str
    bounding_boxes: List[Dict]
    keywords_found: List[Annotation]
    urls_found: List[Annotation]

class PDFProcessor(QObject):
    """Handles PDF processing, rendering, and keyword highlighting."""
    
    # Signals
    page_rendered = pyqtSignal(int, QImage)      # page_number, image
    processing_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)             # error_message
    
    def __init__(self, annotation_manager: AnnotationManager):
        """
        Initialize the PDF processor with a shared AnnotationManager.
        """
        super().__init__()
        self.annotation_manager = annotation_manager
        self._document_mutex = QMutex()
        
        self.document: Optional[fitz.Document] = None
        self.current_file_path: str = ""
        self.page_metadata: Dict[int, PageMetadata] = {}
        self.current_dpi = Config.DEFAULT_DPI
        
    def load_pdf(self, file_path: str) -> bool:
        """
        Open the PDF document and reset state.
        Metadata is loaded on demand.
        """
        try:
            if self.document:
                self.document.close()
            self.document = fitz.open(file_path)
            self.current_file_path = file_path
            self.page_metadata.clear()
            return True
        except Exception:
            logging.exception("Error loading PDF")
            return False
        
    def _ensure_page_metadata(self, page_num: int) -> None:
        """Extract metadata for a single page if not already cached."""
        if page_num in self.page_metadata or not self.document:
            return
        try:
            page = self.document.load_page(page_num)
            text_content = page.get_text()
            blocks = page.get_text("dict").get("blocks", [])
            boxes = []
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        x0, y0, x1, y1 = span["bbox"]
                        boxes.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": span["text"]})
            anns = self.annotation_manager.find_all_annotations_in_text(text_content)
            kws = [a for a in anns if a.annotation_type == AnnotationType.KEYWORD]
            urls = [a for a in anns if a.annotation_type == AnnotationType.URL_VALIDATION]
            self.page_metadata[page_num] = PageMetadata(page_num, text_content, boxes, kws, urls)
        except Exception:
            logging.exception(f"Error extracting metadata for page {page_num}")

    def render_page(self, page_number: int, zoom_level: float = 1.0) -> Optional[QImage]:
        """
        Render a PDF page with highlighting.
        Uses a mutex to protect document access.
        """
        if not self.document or page_number >= len(self.document):
            return None
        with QMutexLocker(self._document_mutex):
            try:
                self._ensure_page_metadata(page_number)
                page = self.document.load_page(page_number)
                dpi = int(self.current_dpi * zoom_level)
                pix = page.get_pixmap(dpi=dpi)
                img_data = pix.tobytes("png")
                pil_image = Image.open(io.BytesIO(img_data))
                # apply highlighting
                image = self._apply_highlighting(pil_image, page_number, zoom_level)
                return self._pil_to_qimage(image)
            except Exception:
                logging.exception(f"Error rendering page {page_number}")
                return None

    def _apply_highlighting(self, image: Image.Image, page_number: int, zoom_level: float) -> Image.Image:
        """Apply keyword and URL highlighting to a PIL Image."""
        meta = self.page_metadata.get(page_number)
        if not meta:
            return image
        draw = ImageDraw.Draw(image)
        scale = zoom_level * (self.current_dpi / 72.0)
        for bbox in meta.bounding_boxes:
            b = {k: int(v * scale) for k, v in bbox.items() if k.startswith("x") or k.startswith("y")}
            annotations = self.annotation_manager.find_all_annotations_in_text(bbox["text"])
            self.annotation_manager.render_annotations(annotations, draw, b)
        return image

    def _pil_to_qimage(self, pil_image: Image.Image) -> QImage:
        """Convert a PIL Image to QImage."""
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        w, h = pil_image.size
        data = pil_image.tobytes("raw", "RGB")
        return QImage(data, w, h, QImage.Format.Format_RGB888)

    def get_page_count(self) -> int:
        return len(self.document) if self.document else 0

    def get_page_metadata(self, page_number: int) -> Optional[PageMetadata]:
        return self.page_metadata.get(page_number)

    def close_document(self):
        if self.document:
            self.document.close()
            self.document = None
            self.current_file_path = ""
            self.page_metadata.clear()
