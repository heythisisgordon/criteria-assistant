# Refactor 11: Migration to Unified Pipeline Architecture

## Goal
Refactor codebase to use a single `PDFPipelineService` for the 8-step PDF workflow, remove redundant layers, clarify metadata extraction, and wire providers/renderers.

---

## Phase 1: Scaffold Service & Models
1. Create `services/PDFPipelineService.py` implementing methods:
   ```python
   class PDFPipelineService:
       def open_document(self, path: str) -> bool
       def get_info(self) -> DocumentInfo      # includes page_metadata for every page
       def load_page(self, page: int) -> bool
       def extract_text(self) -> str
       def find_annotations(self) -> AnnotationSummary
       def render_plain(self, zoom: float) -> PIL.Image
       def apply_annotations(self) -> PIL.Image
       # Note: convert_to_qimage removed from service
       def run_all(self, page: int, zoom: float) -> PIL.Image
   ```
2. Create data models in `models/`:
   - **DocumentInfo**: `page_count`, `title`, `author`, `subject`, `file_path`,  
     `page_metadata: Dict[int, PageMetadata]`
   - **AnnotationSummary**: counts by type (`total`, `keywords`, `urls`)

---

## Phase 2: Integrate Providers, Renderers & Metadata
1. In `MainWindow.__init__`, initialize:
   ```python
   am = AnnotationManager()
   am.register_provider(KEYWORD, KeywordProvider())
   am.register_provider(URL_VALIDATION, URLProvider())
   am.register_renderer(KEYWORD, KeywordRenderer())
   am.register_renderer(URL_VALIDATION, URLRenderer())

   keyword_provider.load_data()
   url_provider.load_data()
   keyword_panel.update_categories()
   keyword_panel.update_url_categories()
   ```
2. Ensure **get_info()**:
   - Calls `PageMetadataBuilder.build()` for each page
   - Populates `DocumentInfo.page_metadata`

---

## Phase 3: Thin Qt Adapter
1. Refactor `PDFProcessor`:
   - Hold a `PDFPipelineService` instance
   - Delegate:
     - `load_pdf(path)` → `pipeline.open_document(path)`
     - `get_page_count()`, `get_page_metadata()` → from last `get_info()`
     - `render_page(page, zoom)` →  
       ```python
       img = pipeline.run_all(page, zoom)
       return convert_to_qimage(img)  # Qt conversion here
       ```
   - Remove `_ensure_page_metadata`, `_apply_highlighting`, and direct `fitz` calls
2. Signals remain unchanged (`page_rendered`, `error_occurred`)

---

## Phase 4: Update DebugPDFProcessor
1. Replace inheritance from `PDFProcessor` with wrapping `PDFPipelineService`
2. Map each debug step to service methods:
   - `'open_document'`, `'get_info'`, …, `'apply_annotations'`
3. Emit `step_completed`/`step_failed` as before

---

## Phase 5: Update MainWindow & PDFRenderWorker
1. Instantiate `pipeline = PDFPipelineService()` and pass to `PDFProcessor`
2. Change `PDFRenderWorker.run()` to:
   ```python
   img = pdf_processor.pipeline.run_all(page, zoom)
   ```
3. Remove any controller-layer code

---

## Phase 6: Cleanup & Remove Obsolete Code
- Delete:
  - Any `PipelineController` or duplicate orchestrator
  - `find_annotations_batch` references
  - `_ensure_page_metadata`, `_apply_highlighting`, legacy text/metadata logic
- Remove unused imports in `pdf_processor.py` and `annotation_system.py`

---

## Phase 7: Testing & Validation
- Unit tests for `PDFPipelineService` steps (mock `fitz.Document`)
- Tests for `AnnotationSummary` and metadata extraction in `get_info()`
- Update existing tests to target new service
- Manual validation via UI and debug toolbar

---

## Phase 8: Documentation & Release
- Update README to describe `PDFPipelineService` API
- Document service usage examples
- Bump version to 2.0.0 and tag release
