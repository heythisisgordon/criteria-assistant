import time
import traceback
import logging
import sys
from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage
import fitz
from PIL import Image

from core.pdf_processor import PDFProcessor
from core.annotation_system import AnnotationManager
from core.config import Config

class DebugPDFProcessor(PDFProcessor):
    """Debug version with atomic step-by-step operations."""
    
    # Debug signals
    step_completed = pyqtSignal(str, dict)  # step_name, metrics
    step_failed = pyqtSignal(str, str, dict)  # step_name, error, context
    
    def __init__(self, annotation_manager: AnnotationManager):
        super().__init__(annotation_manager)
        self.debug_mode = True
        self.step_metrics: Dict[str, Dict[str, Any]] = {}
        self.last_successful_step: Optional[str] = None
        
        # Define step functions using command pattern
        self.debug_steps: Dict[str, Callable] = {
            'open_document': self._step_open_document,
            'get_info': self._step_get_document_info,
            'load_page': self._step_load_single_page,
            'extract_text': self._step_extract_page_text,
            'find_annotations': self._step_find_annotations,
            'render_plain': self._step_render_without_annotations,
            'apply_annotations': self._step_apply_annotations,
            'convert_qimage': self._step_convert_to_qimage
        }
        
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB using built-in method."""
        import resource
        if sys.platform != 'win32':
            # Unix-like systems
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return usage / 1024 if sys.platform == 'darwin' else usage / 1024 / 1024
        else:
            # Windows - use tracemalloc as fallback
            import tracemalloc
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            current, peak = tracemalloc.get_traced_memory()
            return current / 1024 / 1024
        
    def _measure_step(self, step_name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute a step with metrics collection."""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        context = {
            'current_page': getattr(self, 'current_page_num', None),
            'document_path': self.current_file_path,
            'last_successful_step': self.last_successful_step,
            'args': args,
            'kwargs': kwargs
        }
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            end_memory = self._get_memory_usage()
            metrics = {
                'time_ms': (end_time - start_time) * 1000,
                'memory_before_mb': start_memory,
                'memory_after_mb': end_memory,
                'memory_delta_mb': end_memory - start_memory,
                'success': True
            }
            self.step_metrics[step_name] = metrics
            self.last_successful_step = step_name
            self.step_completed.emit(step_name, metrics)
            return result
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.step_failed.emit(step_name, error_msg, context)
            logging.error(f"Step {step_name} failed: {error_msg}\nContext: {context}")
            raise
    
    def execute_step(self, step_name: str, *args, **kwargs) -> Any:
        """Execute a debug step by name."""
        if step_name not in self.debug_steps:
            raise ValueError(f"Unknown step: {step_name}")
        step_func = self.debug_steps[step_name]
        return self._measure_step(step_name, step_func, *args, **kwargs)
    
    # ATOMIC STEP IMPLEMENTATIONS
    
    def _step_open_document(self, file_path: str) -> bool:
        """Step 1: Just open the PDF document."""
        if self.document:
            self.document.close()
        self.document = fitz.open(file_path)
        self.current_file_path = file_path
        return True
    
    def _step_get_document_info(self) -> Dict[str, Any]:
        """Step 2: Get document metadata only."""
        if not self.document:
            raise ValueError("No document loaded")
        metadata = self.document.metadata
        return {
            "page_count": len(self.document),
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "file_path": self.current_file_path
        }
    
    def _step_load_single_page(self, page_num: int) -> bool:
        """Step 3: Load a single page object."""
        if not self.document:
            raise ValueError("No document loaded")
        self.current_page = self.document.load_page(page_num)
        self.current_page_num = page_num
        return True
    
    def _step_extract_page_text(self) -> str:
        """Step 4: Extract text from current page."""
        if not self.current_page:
            raise ValueError("No page loaded")
        text = self.current_page.get_text()
        self.current_page_text = text
        return text
    
    def _step_find_annotations(self) -> Dict[str, int]:
        """Step 5: Find annotations in extracted text."""
        if not self.current_page_text:
            raise ValueError("No text extracted")
        annotations = self.annotation_manager.find_all_annotations_in_text(
            self.current_page_text
        )
        self.current_annotations = annotations
        return {
            "total": len(annotations),
            "keywords": sum(1 for a in annotations if a.annotation_type.value == "keyword"),
            "urls": sum(1 for a in annotations if a.annotation_type.value == "url_validation")
        }
    
    def _step_render_without_annotations(self, zoom_level: float = 1.0) -> Image.Image:
        """Step 6: Render page without annotations."""
        if not self.current_page:
            raise ValueError("No page loaded")
        dpi = int(self.current_dpi * zoom_level)
        pix = self.current_page.get_pixmap(dpi=dpi)
        img_data = pix.tobytes("png")
        import io
        pil_image = Image.open(io.BytesIO(img_data))
        self.current_plain_image = pil_image
        return pil_image
    
    def _step_apply_annotations(self) -> Image.Image:
        """Step 7: Apply annotations to rendered image."""
        if not self.current_plain_image:
            raise ValueError("No plain image rendered")
        return self.current_plain_image
    
    def _step_convert_to_qimage(self) -> QImage:
        """Step 8: Convert PIL image to QImage."""
        if not self.current_plain_image:
            raise ValueError("No image to convert")
        return self._pil_to_qimage(self.current_plain_image)
    
    def get_debug_report(self) -> str:
        """Generate a debug report of all steps."""
        report = ["Debug Report", "=" * 50, ""]
        for step_name, metrics in self.step_metrics.items():
            report.append(f"Step: {step_name}")
            report.append(f"  Time: {metrics['time_ms']:.2f}ms")
            report.append(f"  Memory: {metrics['memory_before_mb']:.2f}MB -> {metrics['memory_after_mb']:.2f}MB")
            report.append(f"  Delta: {metrics['memory_delta_mb']:+.2f}MB")
            report.append("")
        report.append(f"Last Successful Step: {self.last_successful_step}")
        return "\n".join(report)
