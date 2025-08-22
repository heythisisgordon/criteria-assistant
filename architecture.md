# Criteria Assistant Reference Architecture

## Overview
A clean, modular pipeline architecture for PDF processing and annotation, supporting exactly one workflow:
1. **Open PDF** → Load document  
2. **Get Info** → Extract document-level metadata and per-page metadata (bounding boxes)  
3. **Load Page** → Retrieve the page object  
4. **Extract Text** → Extract page text only  
5. **Find Annotations** → Match against providers via `AnnotationManager`  
6. **Render Plain** → Render base image as `PIL.Image`  
7. **Apply Annotations** → Overlay highlights on `PIL.Image`  
8. **Convert to QImage** → Convert `PIL.Image` to `QImage` (in UI layer)  

All steps live in a single service: `PDFPipelineService`. Qt-specific code (signals, widgets, image conversion) remains in the UI layer.

---

## Layers and Modules

### 1. UI Layer
- **MainWindow**:  
  - Sets up `AnnotationManager`, providers, renderers, and data.  
  - Instantiates `PDFProcessor` (thin Qt wrapper).  
- **PDFViewerWidget**: Page display, navigation, and zoom controls.  
- **KeywordPanel**: Annotation category toggles and metadata sidebar.  
- **DebugToolbar & DebugLogWidget**: Optional debug controls triggering individual steps.

### 2. Service Layer
- **PDFPipelineService**:  
  - Implements the 8 atomic steps as methods.  
  - Maintains minimal state:  
    - `document: fitz.Document`  
    - `current_page_num: int`  
  - Each method validates prerequisites (e.g., document loaded).  
- **PDFProcessor**:  
  - `QObject` wrapper around `PDFPipelineService`.  
  - Exposes `run_all(page, zoom)` and signals:  
    - `page_rendered(QImage, int)`  
    - `error_occurred(str)`

### 3. Core Components
- **AnnotationManager**:  
  - Registers providers and renderers.  
  - Thread-safe LRU cache.  
  - Methods:  
    - `find_all_annotations_in_text(text: str) -> List[Annotation]`  
    - `render_annotations(annotations, draw_context, bounds)`  
- **Providers** (`BaseCSVAnnotationProvider` subclasses):  
  - `KeywordProvider`, `URLProvider`  
  - Load CSV data once at startup.  
- **Renderers** (`AnnotationRenderer` implementations):  
  - `KeywordRenderer`, `URLRenderer`  
- **MetadataBuilder**:  
  - `PageMetadataBuilder.build(document, page_num) -> PageMetadata`

### 4. Data Models
- **DocumentInfo**  
  - `page_count`, `title`, `author`, `subject`, `file_path`  
  - `page_metadata: Dict[int, PageMetadata]`  
- **PageMetadata**  
  - `page_index`, `content`, `bounding_boxes`, `keywords_found`, `urls_found`  
- **AnnotationSummary**  
  - Counts by annotation type  

### 5. Threading
- **PDFRenderWorker**  
  - Runs `PDFProcessor.run_all(page, zoom)` on background thread.  
  - Emits `page_rendered` and `error_occurred` signals.

---

## Initialization Flow (in `MainWindow.__init__`)
```python
self.annotation_manager = AnnotationManager()

# Providers
self.keyword_provider = KeywordProvider()
self.url_provider = URLProvider()
self.annotation_manager.register_provider(AnnotationType.KEYWORD, self.keyword_provider)
self.annotation_manager.register_provider(AnnotationType.URL_VALIDATION, self.url_provider)

# Renderers
self.annotation_manager.register_renderer(
    AnnotationType.KEYWORD, KeywordRenderer())
self.annotation_manager.register_renderer(
    AnnotationType.URL_VALIDATION, URLRenderer())

# Load data
self.keyword_provider.load_data()
self.url_provider.load_data()
self.keyword_panel.update_categories()
self.keyword_panel.update_url_categories()
```

---

## Workflow Sequence

1. **Open PDF**  
2. **Get Info** (step 2 populates `DocumentInfo` and all `PageMetadata`)  
3. **Load Page**  
4. **Extract Text**  
5. **Find Annotations**  
6. **Render Plain**  
7. **Apply Annotations**  
8. **Convert to QImage**  

Qt conversion (step 8) occurs in `PDFProcessor`; core service returns `PIL.Image` for steps 6–7.

---

## Benefits
- **Single Service**: one `PDFPipelineService` implements all steps.  
- **Separation of Concerns**: Qt/UI code isolated from core PDF logic.  
- **Minimal State**: only document and page index.  
- **Explicit Data Flow**: metadata extraction in step 2.  
- **Providers & Renderers**: load and register once at startup.  
- **Testability**: each method in `PDFPipelineService` is unit-testable.
