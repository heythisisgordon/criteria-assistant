from typing import Dict, Any, Optional
import fitz
from PIL import Image, ImageDraw
from core.annotation_system import AnnotationManager, AnnotationType
from core.metadata_builder import PageMetadataBuilder
from core.page_metadata import PageMetadata
from models.DocumentInfo import DocumentInfo
from models.AnnotationSummary import AnnotationSummary

class PDFPipelineService:
    """Service implementing the 8-step PDF processing pipeline."""

    def __init__(self, annotation_manager: AnnotationManager):
        self.annotation_manager = annotation_manager
        self.document: fitz.Document | None = None
        self.current_page_num: int = -1
        self.page_metadata: Dict[int, PageMetadata] = {}
        # State for isolated steps
        self.current_text: str = ""
        self.current_image: Optional[Image.Image] = None

    def open_document(self, path: str) -> bool:
        """Step 1: Open PDF document and reset state."""
        try:
            if self.document:
                self.document.close()
            self.document = fitz.open(path)
            self.current_page_num = -1
            self.page_metadata.clear()
            self.current_text = ""
            self.current_image = None
            return True
        except Exception:
            return False

    def get_info(self) -> DocumentInfo:
        """Step 2: Extract document metadata and per-page metadata."""
        if not self.document:
            raise ValueError("No document loaded")
        metadata = self.document.metadata
        page_count = len(self.document)
        builder = PageMetadataBuilder(self.annotation_manager)
        self.page_metadata = {}
        for page_num in range(page_count):
            pm = builder.build(self.document, page_num)
            self.page_metadata[page_num] = pm
        return DocumentInfo(
            page_count=page_count,
            title=metadata.get("title", ""),
            author=metadata.get("author", ""),
            subject=metadata.get("subject", ""),
            file_path=self.document.name,
            page_metadata=self.page_metadata
        )

    def load_page(self, page: int) -> bool:
        """Step 3: Load a specific page object."""
        if not self.document or page < 0 or page >= len(self.document):
            return False
        self.current_page_num = page
        # Clear previous text/image state
        self.current_text = ""
        self.current_image = None
        return True

    def extract_text(self) -> str:
        """Step 4: Extract text from the current page."""
        if self.current_page_num < 0:
            raise ValueError("No page loaded")
        page = self.document.load_page(self.current_page_num)
        text = page.get_text()
        self.current_text = text
        return text

    def find_annotations(self) -> AnnotationSummary:
        """Step 5: Find annotations in the extracted text."""
        if not self.current_text:
            raise ValueError("No text extracted")
        annotations = self.annotation_manager.find_all_annotations_in_text(self.current_text)
        total = len(annotations)
        keywords = sum(1 for a in annotations if a.annotation_type == AnnotationType.KEYWORD)
        urls = sum(1 for a in annotations if a.annotation_type == AnnotationType.URL_VALIDATION)
        return AnnotationSummary(total=total, keywords=keywords, urls=urls)

    def render_plain(self, zoom: float) -> Image.Image:
        """Step 6: Render the page as a PIL.Image without annotations."""
        if self.current_page_num < 0:
            raise ValueError("No page loaded")
        page = self.document.load_page(self.current_page_num)
        dpi = int(72 * zoom)
        pix = page.get_pixmap(dpi=dpi)
        image = Image.open(pix.tobytes("png"))
        self.current_image = image
        return image

    def apply_annotations(self) -> Image.Image:
        """Step 7: Apply annotation highlights to the rendered image."""
        if self.current_image is None:
            raise ValueError("No image rendered")
        image = self.current_image.copy()
        draw = ImageDraw.Draw(image)
        pm = self.page_metadata.get(self.current_page_num)
        if pm:
            for bbox in pm.bounding_boxes:
                bounds = {k: int(v) for k, v in bbox.items() if k.startswith(("x", "y"))}
                anns = bbox.get("annotations", [])
                self.annotation_manager.render_annotations(anns, draw, bounds)
        return image

    def run_all(self, page: int, zoom: float) -> Image.Image:
        """
        Convenience method: execute steps 3–7 in sequence.
        """
        self.load_page(page)
        self.get_info()
        self.extract_text()
        self.find_annotations()
        self.render_plain(zoom)
        return self.apply_annotations()
