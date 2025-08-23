import time
import traceback
import logging
from typing import Any, Dict, Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage
from PIL import Image
import io

from services.PDFPipelineService import PDFPipelineService


logger = logging.getLogger(__name__)


class DebugPDFProcessor(QObject):
    """Debug wrapper executing each pipeline step with metrics."""

    step_completed = pyqtSignal(str, dict)         # step_name, metrics
    step_failed = pyqtSignal(str, str, dict)       # step_name, error, context

    def __init__(self, pipeline: PDFPipelineService):
        super().__init__()
        self.pipeline = pipeline
        self.step_metrics: Dict[str, Dict[str, Any]] = {}
        self.last_successful_step: Optional[str] = None

        # Map step names to methods
        self.debug_steps: Dict[str, Callable[..., Any]] = {
            'open_document': self._step_open_document,
            'get_info': self._step_get_info,
            'load_page': self._step_load_page,
            'extract_text': self._step_extract_text,
            'find_annotations': self._step_find_annotations,
            'render_plain': self._step_render_plain,
            'apply_annotations': self._step_apply_annotations,
            'convert_qimage': self._step_convert_to_qimage,
        }

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import tracemalloc
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            current, _ = tracemalloc.get_traced_memory()
            return current / 1024 / 1024
        except (ImportError, RuntimeError) as e:
            logger.debug("Could not determine memory usage: %s", e)
            return 0.0

    def _measure_step(self, step_name: str, func: Callable, *args, **kwargs) -> Any:
        """Run step, collect timing and memory metrics."""
        start_time = time.time()
        start_mem = self._get_memory_usage()
        context = {'last_successful': self.last_successful_step, 'args': args, 'kwargs': kwargs}
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            end_mem = self._get_memory_usage()
            metrics = {
                'time_ms': (end_time - start_time) * 1000,
                'mem_before_mb': start_mem,
                'mem_after_mb': end_mem,
                'memory_delta_mb': end_mem - start_mem,
                'success': True
            }
            self.step_metrics[step_name] = metrics
            self.last_successful_step = step_name
            self.step_completed.emit(step_name, metrics)
            return result
        except Exception as e:
            error_msg = traceback.format_exc()
            self.step_failed.emit(step_name, error_msg, context)
            logger.exception("Debug step %s failed | Context: %s", step_name, context)
            raise

    def execute_step(self, step_name: str, **params) -> Any:
        """Trigger a named debug step."""
        if step_name not in self.debug_steps:
            raise ValueError(f"Unknown step: {step_name}")
        return self._measure_step(step_name, self.debug_steps[step_name], **params)

    # Step implementations

    def _step_open_document(self, path: str) -> bool:
        """Step 1: Open PDF."""
        return self.pipeline.open_document(path)

    def _step_get_info(self) -> Dict[str, Any]:
        """Step 2: Get document info."""
        info = self.pipeline.get_info()
        # Return basic dict for debug
        return {
            'page_count': info.page_count,
            'title': info.title,
            'author': info.author,
            'subject': info.subject
        }

    def _step_load_page(self, page_num: int) -> bool:
        """Step 3: Load a page."""
        return self.pipeline.load_page(page_num)

    def _step_extract_text(self) -> str:
        """Step 4: Extract text."""
        return self.pipeline.extract_text()

    def _step_find_annotations(self) -> Dict[str, int]:
        """Step 5: Find annotations summary."""
        summary = self.pipeline.find_annotations()
        return {'total': summary.total, 'keywords': summary.keywords, 'urls': summary.urls}

    def _step_render_plain(self, zoom: float = 1.0) -> Image.Image:
        """Step 6: Render page without annotations."""
        return self.pipeline.render_plain(zoom)

    def _step_apply_annotations(self) -> Image.Image:
        """Step 7: Apply annotations."""
        return self.pipeline.apply_annotations()

    def _step_convert_to_qimage(self) -> QImage:
        """Step 8: Convert the last image to QImage."""
        # Assume last step provided PIL Image in self.step_metrics context? Fall back to render_plain
        pil_img = self.pipeline.render_plain(1.0)
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        w, h = pil_img.size
        data = pil_img.tobytes('raw', 'RGB')
        return QImage(data, w, h, QImage.Format.Format_RGB888)
