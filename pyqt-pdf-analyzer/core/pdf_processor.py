"""
PDF processing and highlighting functionality.
Handles PDF loading, rendering, and keyword highlighting.
"""

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QObject, pyqtSignal
import io
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from core.keyword_manager import KeywordManager, Keyword
from core.config import Config

@dataclass
class PageMetadata:
    """Metadata for a PDF page."""
    page_number: int
    content: str
    bounding_boxes: List[Dict]
    keywords_found: List[Keyword]

class PDFProcessor(QObject):
    """Handles PDF processing, rendering, and keyword highlighting."""
    
    # Signals
    page_rendered = pyqtSignal(int, QPixmap)  # page_number, pixmap
    processing_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, keyword_manager: KeywordManager):
        """
        Initialize the PDF processor.
        
        Args:
            keyword_manager: KeywordManager instance for keyword detection.
        """
        super().__init__()
        self.keyword_manager = keyword_manager
        self.document: Optional[fitz.Document] = None
        self.current_file_path: str = ""
        self.page_metadata: Dict[int, PageMetadata] = {}
        self.current_dpi = Config.DEFAULT_DPI
        
    def load_pdf(self, file_path: str) -> bool:
        """
        Load a PDF file.
        
        Args:
            file_path: Path to the PDF file.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if self.document:
                self.document.close()
                
            self.document = fitz.open(file_path)
            self.current_file_path = file_path
            self.page_metadata.clear()
            
            # Extract text and metadata for all pages
            self._extract_page_metadata()
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Error loading PDF: {str(e)}")
            return False
    
    def _extract_page_metadata(self):
        """Extract text content and metadata from all pages."""
        if not self.document:
            return
            
        for page_num in range(len(self.document)):
            try:
                page = self.document.load_page(page_num)
                
                # Extract text content
                text_content = page.get_text()
                
                # Get text blocks with bounding boxes
                blocks = page.get_text("dict")
                bounding_boxes = []
                
                for block in blocks.get("blocks", []):
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                bbox = {
                                    "x0": span["bbox"][0],
                                    "y0": span["bbox"][1], 
                                    "x1": span["bbox"][2],
                                    "y1": span["bbox"][3],
                                    "text": span["text"]
                                }
                                bounding_boxes.append(bbox)
                
                # Find keywords in the text
                keywords_found = self.keyword_manager.find_keywords_in_text(text_content)
                
                # Store metadata
                self.page_metadata[page_num] = PageMetadata(
                    page_number=page_num,
                    content=text_content,
                    bounding_boxes=bounding_boxes,
                    keywords_found=keywords_found
                )
                
            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
    
    def render_page(self, page_number: int, zoom_level: float = 1.0) -> Optional[QPixmap]:
        """
        Render a PDF page with keyword highlighting.
        
        Args:
            page_number: Page number to render (0-based).
            zoom_level: Zoom level for rendering.
            
        Returns:
            QPixmap of the rendered page, or None if error.
        """
        if not self.document or page_number >= len(self.document):
            return None
            
        try:
            page = self.document.load_page(page_number)
            
            # Calculate DPI based on zoom level
            dpi = int(self.current_dpi * zoom_level)
            
            # Render page to pixmap
            pix = page.get_pixmap(dpi=dpi)
            
            # Convert to PIL Image for highlighting
            img_data = pix.tobytes("png")
            pil_image = Image.open(io.BytesIO(img_data))
            
            # Apply keyword highlighting
            highlighted_image = self._apply_keyword_highlighting(
                pil_image, page_number, zoom_level
            )
            
            # Convert back to QPixmap
            qimage = self._pil_to_qimage(highlighted_image)
            pixmap = QPixmap.fromImage(qimage)
            
            return pixmap
            
        except Exception as e:
            self.error_occurred.emit(f"Error rendering page {page_number}: {str(e)}")
            return None
    
    def _apply_keyword_highlighting(self, image: Image.Image, page_number: int, zoom_level: float) -> Image.Image:
        """
        Apply keyword highlighting to a PIL image.
        
        Args:
            image: PIL Image to highlight.
            page_number: Page number being processed.
            zoom_level: Current zoom level.
            
        Returns:
            PIL Image with highlighting applied.
        """
        if page_number not in self.page_metadata:
            return image
            
        draw = ImageDraw.Draw(image)
        metadata = self.page_metadata[page_number]
        
        # Use default font
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        # Scale factor for bounding boxes based on zoom
        scale_factor = zoom_level * (self.current_dpi / 72.0)  # PDF points to pixels
        
        # Highlight text blocks containing keywords
        for bbox in metadata.bounding_boxes:
            text_content = bbox["text"].lower()
            
            # Check if this text block contains any enabled keywords
            found_keywords = self.keyword_manager.find_keywords_in_text(text_content)
            
            if found_keywords:
                # Use the first keyword's color for highlighting
                keyword = found_keywords[0]
                color = keyword.color
                
                # Scale bounding box coordinates
                x0 = int(bbox["x0"] * scale_factor)
                y0 = int(bbox["y0"] * scale_factor)
                x1 = int(bbox["x1"] * scale_factor)
                y1 = int(bbox["y1"] * scale_factor)
                
                # Draw highlight rectangle
                highlight_color = self._hex_to_rgba(color, alpha=80)  # Semi-transparent
                draw.rectangle([x0, y0, x1, y1], fill=highlight_color, outline=color, width=2)
                
                # Draw category label
                if font:
                    label = f" {keyword.category} "
                    
                    # Get text size (fallback for older Pillow versions)
                    try:
                        bbox_size = draw.textbbox((0, 0), label, font=font)
                        text_width = bbox_size[2] - bbox_size[0]
                        text_height = bbox_size[3] - bbox_size[1]
                    except AttributeError:
                        # Fallback for older Pillow versions
                        text_width, text_height = draw.textsize(label, font=font)
                    
                    # Position label above the highlighted text
                    label_x = x0
                    label_y = max(0, y0 - text_height - 6)
                    
                    # Draw label background
                    label_bg = [label_x, label_y, label_x + text_width + 4, label_y + text_height + 4]
                    draw.rounded_rectangle(label_bg, radius=8, fill=color)
                    
                    # Draw label text
                    draw.text((label_x + 2, label_y + 2), label, fill="white", font=font)
        
        return image
    
    def _hex_to_rgba(self, hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
        """
        Convert hex color to RGBA tuple.
        
        Args:
            hex_color: Hex color string (e.g., "#FF0000").
            alpha: Alpha value (0-255).
            
        Returns:
            RGBA tuple.
        """
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b, alpha)
        return (128, 128, 128, alpha)  # Default gray
    
    def _pil_to_qimage(self, pil_image: Image.Image) -> QImage:
        """
        Convert PIL Image to QImage.
        
        Args:
            pil_image: PIL Image to convert.
            
        Returns:
            QImage object.
        """
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Get image data
        width, height = pil_image.size
        rgb_data = pil_image.tobytes('raw', 'RGB')
        
        # Create QImage
        qimage = QImage(rgb_data, width, height, QImage.Format.Format_RGB888)
        return qimage
    
    def get_page_count(self) -> int:
        """Get the total number of pages in the loaded PDF."""
        return len(self.document) if self.document else 0
    
    def get_page_metadata(self, page_number: int) -> Optional[PageMetadata]:
        """Get metadata for a specific page."""
        return self.page_metadata.get(page_number)
    
    def get_document_info(self) -> Dict:
        """Get document metadata information."""
        if not self.document:
            return {}
            
        metadata = self.document.metadata
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_count": len(self.document),
            "file_path": self.current_file_path
        }
    
    def set_dpi(self, dpi: int):
        """Set the DPI for PDF rendering."""
        self.current_dpi = max(72, min(600, dpi))  # Clamp between 72 and 600
    
    def close_document(self):
        """Close the current PDF document."""
        if self.document:
            self.document.close()
            self.document = None
            self.current_file_path = ""
            self.page_metadata.clear()
