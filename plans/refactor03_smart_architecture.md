# Smart Engineering Approach: Extensible Annotation Framework

## Overview
This plan implements a generic annotation system that can handle keywords, URLs, and future annotation types through a clean, extensible architecture. The approach follows SOLID principles and allows incremental implementation without over-engineering.

## Core Architecture Principles

### 1. **Generic Annotation Abstraction**
All annotations (keywords, URLs, future types) share common characteristics:
- Text matching/detection logic
- Visual rendering properties (color, style)
- Categorization and filtering
- Enable/disable functionality

### 2. **Incremental Implementation**
- **Phase 1**: Refactor existing keyword system into annotation framework
- **Phase 2**: Add URL validation as second annotation type  
- **Phase 3**: Add advanced features and new annotation types

### 3. **SOLID Compliance**
- **Single Responsibility**: Each component has one clear purpose
- **Open/Closed**: Easy to add new annotation types without modifying existing code
- **Liskov Substitution**: All annotation types are interchangeable
- **Interface Segregation**: Clean, focused interfaces
- **Dependency Inversion**: Depend on abstractions, not implementations

## Phase 1: Core Annotation Framework

### 1.1 Base Annotation System (`core/annotation_system.py`)

**Core Abstractions**:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Set, Any, Optional
from enum import Enum

class AnnotationType(Enum):
    KEYWORD = "keyword"
    URL_VALIDATION = "url_validation"
    REFERENCE = "reference"  # Future
    ERROR = "error"          # Future

@dataclass
class Annotation:
    """Base annotation data structure."""
    text: str
    annotation_type: AnnotationType
    category: str
    color: str
    metadata: Dict[str, Any]
    enabled: bool = True
    
    def __post_init__(self):
        """Validate annotation data."""
        if not self.text or not self.category:
            raise ValueError("Annotation must have text and category")

class AnnotationProvider(ABC):
    """Abstract base for annotation data providers."""
    
    @abstractmethod
    def load_data(self, source_path: str = None) -> bool:
        """Load annotation data from source."""
        pass
    
    @abstractmethod
    def find_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find all annotations in the given text."""
        pass
    
    @abstractmethod
    def get_categories(self) -> Set[str]:
        """Get all available categories."""
        pass
    
    @abstractmethod
    def get_enabled_categories(self) -> Set[str]:
        """Get currently enabled categories."""
        pass
    
    @abstractmethod
    def set_category_enabled(self, category: str, enabled: bool):
        """Enable/disable a category."""
        pass

class AnnotationRenderer(ABC):
    """Abstract base for annotation rendering."""
    
    @abstractmethod
    def render_annotation(self, annotation: Annotation, draw_context: Any, bounds: Dict[str, int]):
        """Render a single annotation."""
        pass
    
    @abstractmethod
    def get_render_priority(self) -> int:
        """Get rendering priority (lower = background, higher = foreground)."""
        pass

class AnnotationManager:
    """Central manager for all annotation types."""
    
    def __init__(self):
        self.providers: Dict[AnnotationType, AnnotationProvider] = {}
        self.renderers: Dict[AnnotationType, AnnotationRenderer] = {}
        self._annotation_cache: Dict[str, List[Annotation]] = {}
    
    def register_provider(self, annotation_type: AnnotationType, provider: AnnotationProvider):
        """Register an annotation provider."""
        self.providers[annotation_type] = provider
        self._clear_cache()
    
    def register_renderer(self, annotation_type: AnnotationType, renderer: AnnotationRenderer):
        """Register an annotation renderer."""
        self.renderers[annotation_type] = renderer
    
    def find_all_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find all annotations from all providers."""
        if text in self._annotation_cache:
            return self._annotation_cache[text]
        
        all_annotations = []
        for provider in self.providers.values():
            annotations = provider.find_annotations_in_text(text)
            all_annotations.extend(annotations)
        
        # Sort by render priority for consistent layering
        all_annotations.sort(key=lambda a: self.renderers[a.annotation_type].get_render_priority())
        
        self._annotation_cache[text] = all_annotations
        return all_annotations
    
    def render_annotations(self, annotations: List[Annotation], draw_context: Any, bounds: Dict[str, int]):
        """Render all annotations in priority order."""
        for annotation in annotations:
            if annotation.enabled:
                renderer = self.renderers.get(annotation.annotation_type)
                if renderer:
                    renderer.render_annotation(annotation, draw_context, bounds)
    
    def get_all_categories(self) -> Dict[AnnotationType, Set[str]]:
        """Get categories from all providers."""
        return {
            ann_type: provider.get_categories() 
            for ann_type, provider in self.providers.items()
        }
    
    def _clear_cache(self):
        """Clear annotation cache when providers change."""
        self._annotation_cache.clear()
```

### 1.2 Keyword Annotation Provider (`core/keyword_provider.py`)

**Refactored from existing KeywordManager**:
```python
import pandas as pd
from typing import List, Set
from core.annotation_system import AnnotationProvider, Annotation, AnnotationType
from core.config import Config

class KeywordProvider(AnnotationProvider):
    """Provides keyword-based annotations."""
    
    def __init__(self):
        self.keywords_df: pd.DataFrame = pd.DataFrame()
        self.enabled_categories: Set[str] = set()
        self._keyword_lookup: Dict[str, List[Annotation]] = {}
    
    def load_data(self, source_path: str = None) -> bool:
        """Load keywords from CSV file."""
        if source_path is None:
            source_path = Config.get_keywords_path()
        
        try:
            self.keywords_df = pd.read_csv(source_path)
            required_cols = ['keyword', 'category', 'color']
            
            if not all(col in self.keywords_df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            
            # Build lookup and enable all categories
            self._build_keyword_lookup()
            self.enabled_categories = set(self.keywords_df['category'].unique())
            return True
            
        except Exception as e:
            print(f"Error loading keywords: {e}")
            return False
    
    def _build_keyword_lookup(self):
        """Build efficient keyword lookup structure."""
        self._keyword_lookup.clear()
        
        for _, row in self.keywords_df.iterrows():
            keyword_text = str(row['keyword']).lower()
            annotation = Annotation(
                text=keyword_text,
                annotation_type=AnnotationType.KEYWORD,
                category=str(row['category']),
                color=str(row['color']),
                metadata={'original_text': str(row['keyword'])}
            )
            
            if keyword_text not in self._keyword_lookup:
                self._keyword_lookup[keyword_text] = []
            self._keyword_lookup[keyword_text].append(annotation)
    
    def find_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find keyword annotations in text."""
        if not text:
            return []
        
        found_annotations = []
        text_lower = text.lower()
        
        for keyword, annotations in self._keyword_lookup.items():
            if keyword in text_lower:
                for annotation in annotations:
                    if annotation.category in self.enabled_categories:
                        found_annotations.append(annotation)
        
        return found_annotations
    
    def get_categories(self) -> Set[str]:
        """Get all keyword categories."""
        return set(self.keywords_df['category'].unique()) if not self.keywords_df.empty else set()
    
    def get_enabled_categories(self) -> Set[str]:
        """Get enabled keyword categories."""
        return self.enabled_categories.copy()
    
    def set_category_enabled(self, category: str, enabled: bool):
        """Enable/disable a keyword category."""
        if enabled:
            self.enabled_categories.add(category)
        else:
            self.enabled_categories.discard(category)
```

### 1.3 URL Validation Provider (`core/url_provider.py`)

**New provider for URL annotations**:
```python
import pandas as pd
import re
from typing import List, Set, Dict, Optional
from core.annotation_system import AnnotationProvider, Annotation, AnnotationType
from core.config import Config

class URLProvider(AnnotationProvider):
    """Provides URL validation annotations."""
    
    def __init__(self):
        self.validations_df: pd.DataFrame = pd.DataFrame()
        self.enabled_categories: Set[str] = set()
        self._url_lookup: Dict[str, Annotation] = {}
        
        # URL detection patterns
        self.url_patterns = [
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            r'www\.[^\s<>"{}|\\^`\[\]]+',
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?',
            r'mailto:[^\s<>"{}|\\^`\[\]]+'
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.url_patterns]
    
    def load_data(self, source_path: str = None) -> bool:
        """Load URL validation data from CSV."""
        if source_path is None:
            source_path = Config.get_url_validation_path()
        
        try:
            self.validations_df = pd.read_csv(source_path)
            required_cols = ['url', 'status', 'final_url', 'is_wbdg', 'check_certainty']
            
            if not all(col in self.validations_df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            
            self._build_url_lookup()
            self.enabled_categories = set(self.validations_df['status'].unique())
            return True
            
        except Exception as e:
            print(f"Error loading URL validations: {e}")
            return False
    
    def _build_url_lookup(self):
        """Build URL lookup structure."""
        self._url_lookup.clear()
        
        for _, row in self.validations_df.iterrows():
            url = str(row['url'])
            status = str(row['status'])
            
            annotation = Annotation(
                text=url,
                annotation_type=AnnotationType.URL_VALIDATION,
                category=status,
                color=Config.get_color_for_status(status),
                metadata={
                    'response_code': row.get('response_code'),
                    'final_url': str(row['final_url']),
                    'error_message': row.get('error_message'),
                    'is_wbdg': bool(row['is_wbdg']),
                    'check_certainty': str(row['check_certainty'])
                }
            )
            
            self._url_lookup[url] = annotation
    
    def find_annotations_in_text(self, text: str) -> List[Annotation]:
        """Find URL annotations in text."""
        if not text:
            return []
        
        found_annotations = []
        
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                url_text = match.group().strip()
                url_text = re.sub(r'<[^>]+>', '', url_text)
                url_text = url_text.rstrip('.,;:!?')
                
                annotation = self._url_lookup.get(url_text)
                if annotation and annotation.category in self.enabled_categories:
                    found_annotations.append(annotation)
        
        return found_annotations
    
    def get_categories(self) -> Set[str]:
        """Get all URL status categories."""
        return set(self.validations_df['status'].unique()) if not self.validations_df.empty else set()
    
    def get_enabled_categories(self) -> Set[str]:
        """Get enabled URL categories."""
        return self.enabled_categories.copy()
    
    def set_category_enabled(self, category: str, enabled: bool):
        """Enable/disable a URL status category."""
        if enabled:
            self.enabled_categories.add(category)
        else:
            self.enabled_categories.discard(category)
```

### 1.4 Annotation Renderers (`core/annotation_renderers.py`)

**Rendering implementations**:
```python
from PIL import ImageDraw, ImageFont
from core.annotation_system import AnnotationRenderer, Annotation, AnnotationType

class KeywordRenderer(AnnotationRenderer):
    """Renders keyword annotations as highlighted pills."""
    
    def get_render_priority(self) -> int:
        """Keywords render on top (higher priority)."""
        return 100
    
    def render_annotation(self, annotation: Annotation, draw_context: ImageDraw.Draw, bounds: Dict[str, int]):
        """Render keyword as highlighted pill."""
        x0, y0, x1, y1 = bounds['x0'], bounds['y0'], bounds['x1'], bounds['y1']
        color = annotation.color
        
        # Semi-transparent highlight
        highlight_color = self._hex_to_rgba(color, alpha=80)
        draw_context.rectangle([x0, y0, x1, y1], fill=highlight_color, outline=color, width=2)
        
        # Category label pill
        try:
            font = ImageFont.load_default()
            label = f" {annotation.category} "
            
            # Get text dimensions
            try:
                bbox_size = draw_context.textbbox((0, 0), label, font=font)
                text_width = bbox_size[2] - bbox_size[0]
                text_height = bbox_size[3] - bbox_size[1]
            except AttributeError:
                text_width, text_height = draw_context.textsize(label, font=font)
            
            # Position label above highlighted text
            label_x = x0
            label_y = max(0, y0 - text_height - 6)
            
            # Draw label background and text
            label_bg = [label_x, label_y, label_x + text_width + 4, label_y + text_height + 4]
            draw_context.rounded_rectangle(label_bg, radius=8, fill=color)
            draw_context.text((label_x + 2, label_y + 2), label, fill="white", font=font)
            
        except Exception:
            pass  # Fallback to just the highlight if text rendering fails
    
    def _hex_to_rgba(self, hex_color: str, alpha: int = 255) -> tuple:
        """Convert hex color to RGBA tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (r, g, b, alpha)
        return (128, 128, 128, alpha)  # Default gray

class URLRenderer(AnnotationRenderer):
    """Renders URL annotations as status borders with indicators."""
    
    def get_render_priority(self) -> int:
        """URLs render in background (lower priority)."""
        return 50
    
    def render_annotation(self, annotation: Annotation, draw_context: ImageDraw.Draw, bounds: Dict[str, int]):
        """Render URL as status border with indicator dot."""
        x0, y0, x1, y1 = bounds['x0'], bounds['y0'], bounds['x1'], bounds['y1']
        color = annotation.color
        
        # Status border (thicker than keyword borders)
        draw_context.rectangle([x0-2, y0-2, x1+2, y1+2], outline=color, width=3)
        
        # Status indicator dot
        dot_size = 8
        dot_x = x1 - dot_size - 2
        dot_y = y0 + 2
        draw_context.ellipse([dot_x, dot_y, dot_x + dot_size, dot_y + dot_size], 
                           fill=color, outline="white", width=1)
```

## Phase 2: Integration with Existing System

### 2.1 Updated Configuration (`core/config.py`)

**Add URL validation support**:
```python
# Add to existing Config class

# URL validation colors
URL_STATUS_COLORS = {
    "PASS": "#00AA00",
    "FAIL": "#CC0000", 
    "WARN_WBDG_CONTENT_ERROR": "#FF8800",
    "EMAIL": "#0066CC",
    "INVALID": "#808080",
    "PROCESSING_ERROR": "#404040",
    "BATCH_MISSING_RESULT": "#666666",
    "NOT_MAPPED": "#999999"
}

# Default paths
DEFAULT_URL_VALIDATION_PATH = "../streamlit-test/data/url_validation_results.csv"

@classmethod
def get_url_validation_path(cls) -> str:
    """Get the path to the URL validation CSV file."""
    return os.path.abspath(cls.DEFAULT_URL_VALIDATION_PATH)

@classmethod
def get_color_for_status(cls, status: str) -> str:
    """Get the highlight color for a URL status."""
    return cls.URL_STATUS_COLORS.get(status, "#808080")
```

### 2.2 Updated PDF Processor (`core/pdf_processor.py`)

**Replace keyword-specific logic with annotation system**:
```python
from core.annotation_system import AnnotationManager, AnnotationType
from core.keyword_provider import KeywordProvider
from core.url_provider import URLProvider
from core.annotation_renderers import KeywordRenderer, URLRenderer

class PDFProcessor(QObject):
    def __init__(self):
        super().__init__()
        
        # Initialize annotation system
        self.annotation_manager = AnnotationManager()
        
        # Register providers
        self.keyword_provider = KeywordProvider()
        self.url_provider = URLProvider()
        self.annotation_manager.register_provider(AnnotationType.KEYWORD, self.keyword_provider)
        self.annotation_manager.register_provider(AnnotationType.URL_VALIDATION, self.url_provider)
        
        # Register renderers
        self.annotation_manager.register_renderer(AnnotationType.KEYWORD, KeywordRenderer())
        self.annotation_manager.register_renderer(AnnotationType.URL_VALIDATION, URLRenderer())
        
        # Load default data
        self.keyword_provider.load_data()
        self.url_provider.load_data()
        
        # ... rest of existing initialization
    
    def _extract_annotation_metadata(self):
        """Extract annotation data from all pages."""
        if not self.document:
            return
            
        for page_num in range(len(self.document)):
            try:
                page = self.document.load_page(page_num)
                text_content = page.get_text()
                
                # Find all annotations
                annotations = self.annotation_manager.find_all_annotations_in_text(text_content)
                
                # Update page metadata
                if page_num in self.page_metadata:
                    self.page_metadata[page_num].annotations = annotations
                
            except Exception as e:
                print(f"Error processing annotations on page {page_num}: {e}")
    
    def _apply_annotations(self, image: Image.Image, page_number: int, zoom_level: float) -> Image.Image:
        """Apply all annotations to the image."""
        if page_number not in self.page_metadata:
            return image
            
        draw = ImageDraw.Draw(image)
        metadata = self.page_metadata[page_number]
        scale_factor = zoom_level * (self.current_dpi / 72.0)
        
        # Render annotations for each text block
        for bbox in metadata.bounding_boxes:
            text_content = bbox["text"]
            annotations = self.annotation_manager.find_all_annotations_in_text(text_content)
            
            if annotations:
                # Scale bounding box coordinates
                bounds = {
                    'x0': int(bbox["x0"] * scale_factor),
                    'y0': int(bbox["y0"] * scale_factor),
                    'x1': int(bbox["x1"] * scale_factor),
                    'y1': int(bbox["y1"] * scale_factor)
                }
                
                # Render all annotations (in priority order)
                self.annotation_manager.render_annotations(annotations, draw, bounds)
        
        return image
```

### 2.3 Updated Main Window (`ui/main_window.py`)

**Simplified integration**:
```python
def __init__(self):
    super().__init__()
    
    # Initialize PDF processor with annotation system
    self.pdf_processor = PDFProcessor()
    
    # ... rest of existing initialization

def load_url_validations(self):
    """Load URL validations from a CSV file."""
    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "Load URL Validations CSV",
        "",
        "CSV Files (*.csv);;All Files (*)"
    )
    
    if file_path:
        if self.pdf_processor.url_provider.load_data(file_path):
            self.keyword_panel.update_annotation_categories()
            self.status_bar.showMessage(f"URL validations loaded from: {os.path.basename(file_path)}")
            self._render_current_page()
        else:
            QMessageBox.critical(
                self,
                "Error Loading URL Validations", 
                f"Could not load URL validations from:\n{file_path}"
            )
```

## Phase 3: Future Extensions

### 3.1 Easy Addition of New Annotation Types

**Example: Reference Annotations**:
```python
class ReferenceProvider(AnnotationProvider):
    """Provides document reference annotations."""
    
    def load_data(self, source_path: str = None) -> bool:
        # Load reference data (standards, regulations, etc.)
        pass
    
    def find_annotations_in_text(self, text: str) -> List[Annotation]:
        # Find references like "ASTM D1234", "UFC 4-010-01", etc.
        pass

# Register with annotation manager
annotation_manager.register_provider(AnnotationType.REFERENCE, ReferenceProvider())
annotation_manager.register_renderer(AnnotationType.REFERENCE, ReferenceRenderer())
```

### 3.2 Plugin Architecture Potential

The system can easily support:
- External annotation providers (databases, APIs)
- Custom rendering styles
- User-defined annotation types
- Import/export of annotation configurations

## Benefits of This Architecture

### ✅ **Extensibility**
- Add new annotation types without modifying existing code
- Support multiple data sources and formats
- Plugin-style architecture

### ✅ **Maintainability** 
- Clear separation of concerns
- Single responsibility for each component
- Easy to test and debug

### ✅ **Performance**
- Efficient caching and lookup structures
- Render priority system prevents conflicts
- Minimal overhead for unused annotation types

### ✅ **User Experience**
- Consistent interface for all annotation types
- Unified enable/disable controls
- Layered rendering without visual conflicts

### ✅ **Future-Proof**
- Easy to add document references, error highlights, regulatory citations
- Support for complex annotation relationships
- Scalable to large document sets

This architecture provides the foundation for a powerful, extensible annotation system while maintaining simplicity in the initial implementation.
