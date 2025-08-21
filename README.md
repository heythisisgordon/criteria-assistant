# Criteria Assistant

A toolkit for building and annotating federal facility document knowledge graphs and viewing PDFs with live annotations.

## Code Orientation

- **pyqt-pdf-analyzer/**  
  - `main.py`: Application entry; sets up logging and starts the Qt event loop.  
  - `core/`  
    - `annotation_system.py`: Defines `Annotation`, `AnnotationProvider`, and `AnnotationManager`.  
    - `keyword_provider.py`, `url_provider.py`: Load CSV data and find annotations in text.  
    - `pdf_processor.py`: Loads and renders PDFs with layered annotations. Emits full tracebacks on error.  
    - `config.py`: Paths, colors, and UI constants.  
  - `ui/`  
    - `main_window.py`: Menu, toolbar, status bar, and orchestrates PDF loading and annotation rendering threads.  
    - `pdf_viewer.py`: Scrollable widget displaying pages, zoom controls, and page navigation.  
    - `keyword_panel.py`: Sidebar for toggling annotation categories and viewing metadata per page.

- **streamlit-test/**
  Prototype Streamlit app demonstrating keyword and URL highlighting using the same core logic.

- **data/**
  CSV/TTL/JSON-LD sources for building the document hierarchy knowledge graph.

- **src/**
  Jupyter notebooks for UFC/UFGS utilities with matching Python scripts (e.g.,
  `UFC_DownloadAllWithMetadata_v2.py`, `UFGS_Extract_Unified_Master_Reference_List_vFINAL.py`,
  `UFGS_CheckAllURLs_v4.py`).

## Quick Start

1. `pip install -r pyqt-pdf-analyzer/requirements.txt`  
2. `python pyqt-pdf-analyzer/main.py`  
3. File → Load Keywords / Load URL Validations  
4. File → Open PDF (load a UFC/UFGS spec)  
5. Toggle annotation categories in the sidebar

License: Public domain
