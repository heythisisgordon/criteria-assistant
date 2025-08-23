import fitz
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QImage
from PIL import Image
from services.PDFPipelineService import PDFPipelineService

class PDFProcessor(QObject):
    """Thin Qt wrapper around PDFPipelineService."""

    # Signals for UI updates
    page_rendered = pyqtSignal(int, QImage)  # page_number, image
    error_occurred = pyqtSignal(str)         # error_message

    def __init__(self, pipeline: PDFPipelineService):
        """
        Initialize with a shared PDFPipelineService instance.
        """
        super().__init__()
        self.pipeline = pipeline
        self._mutex = QMutex()

    @property
    def document(self):
        """Provide access to the underlying document."""
        return self.pipeline.document

    def load_pdf(self, path: str) -> bool:
        """
        Step 1: Open PDF document.
        """
        with QMutexLocker(self._mutex):
            success = self.pipeline.open_document(path)
            return success

    def get_page_count(self) -> int:
        """
        Retrieve total page count after metadata extraction.
        """
        try:
            info = self.pipeline.get_info()
            return info.page_count
        except Exception as e:
            self.error_occurred.emit(str(e))
            return 0

    def get_page_metadata(self, page: int):
        """
        Get PageMetadata for a given page index.
        """
        return self.pipeline.page_metadata.get(page)

    def render_page(self, page_number: int, zoom_level: float) -> QImage:
        """
        Steps 3–8: Load page, extract text, find annotations,
        render plain image, apply annotations, convert to QImage.
        """
        with QMutexLocker(self._mutex):
            try:
                pil_img = self.pipeline.run_all(page_number, zoom_level)
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                w, h = pil_img.size
                data = pil_img.tobytes("raw", "RGB")
                qimg = QImage(data, w, h, QImage.Format.Format_RGB888)
                return qimg
            except Exception as e:
                self.error_occurred.emit(str(e))
                return None

    def close_document(self):
        """
        Close the current document and clear state.
        """
        with QMutexLocker(self._mutex):
            if self.pipeline.document:
                self.pipeline.document.close()
                self.pipeline.document = None
                self.pipeline.page_metadata.clear()
