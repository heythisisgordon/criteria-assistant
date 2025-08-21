# Refactor 05: Full Annotation Framework Adoption

## Overview
This document completes the migration to the generic annotation framework across UI, controllers, and PDF processing. It ensures all legacy `KeywordManager` APIs are deprecated, and the application exclusively uses `AnnotationManager`, `KeywordProvider`, and `URLProvider`.

## Goals
- Migrate all UI panels (KeywordPanel, MainWindow, PDFViewer) to use `AnnotationManager` and providers exclusively  
- Deprecate and remove legacy `KeywordManager` methods from UI and application entry points  
- Harmonize imports and type hints to use `Annotation`, `AnnotationType`, `KeywordProvider`, `URLProvider`  
- Preserve existing functionality and performance  
- Clean up unused code paths and documentation

## Phase 1: UI Panel Refactoring
1. **KeywordPanel**  
   - Replace calls to `keyword_manager.get_categories()` with `annotation_manager.get_all_categories()[AnnotationType.KEYWORD]`  
   - Replace category toggles to call `keyword_provider.set_category_enabled(category, enabled)`  
   - Replace URL section to use `annotation_manager.get_all_categories()[AnnotationType.URL_VALIDATION]` and `url_provider.set_category_enabled(status, enabled)`  
   - Update metadata display to list combined annotations via `annotation_manager.find_all_annotations_in_text(text)`  
2. **PDFViewer** (if separate)  
   - Wire rendering controls to use `AnnotationManager.render_annotations`  

## Phase 2: MainWindow & Controllers
1. Instantiate and configure framework in `ui/main_window.py`:  
   ```python
   annotation_manager = AnnotationManager()
   keyword_provider = KeywordProvider()
   url_provider = URLProvider()
   annotation_manager.register_provider(AnnotationType.KEYWORD, keyword_provider)
   annotation_manager.register_provider(AnnotationType.URL_VALIDATION, url_provider)
   # register renderers...
   keyword_provider.load_data()
   url_provider.load_data()
   ```
2. Pass `annotation_manager`, `keyword_provider`, and `url_provider` into panels and `PDFProcessor`  
3. Replace legacy calls:  
   - `keyword_manager.load_keywords(...)` → `keyword_provider.load_data(...)`  
   - `keyword_manager.load_url_validations(...)` → `url_provider.load_data(...)`  

## Phase 3: PDFProcessor & Viewer Integration
- Remove direct `KeywordManager` usage in `core/pdf_processor.py` and UI  
- Ensure PDFProcessor uses `annotation_manager.find_all_annotations_in_text` and `render_annotations` exclusively  
- Update any viewer callbacks to consume unified `PageMetadata.annotations`  

## Phase 4: Cleanup & Removal
- Remove unused legacy methods from `core/keyword_manager.py` (e.g., `find_keywords_in_text`, URL methods)  
- Delete imports of `KeywordManager` and `URLValidation` from UI files  
- Remove or archive old code sections in comments  
- Update `requirements.txt` if dependencies changed  

## Phase 5: Validation & Documentation
- Manual UI walkthrough covering keywords and URL toggling  
- Automated tests (if present) updated to use new APIs  
- Update README, examples, and this plan with usage snippets  
- Confirm performance metrics meet or exceed previous version
