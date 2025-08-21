# Criteria Assistant

A toolkit for building and annotating federal facility document knowledge graphs and viewing PDFs with live annotations.

## Code Orientation

- **pyqt-pdf-analyzer/**
  - `main.py`: Application entry; sets up logging and starts the Qt event loop.
  - `ui/`
    - `main_window.py`: Menu, toolbar, status bar, and orchestrates PDF loading and annotation rendering threads.
    - `pdf_viewer.py`: Scrollable widget displaying pages, zoom controls, and page navigation.
    - `keyword_panel.py`: Sidebar for toggling annotation categories and viewing metadata per page.

- **src/core/**
  Shared annotation, provider, and PDF processing logic.

- **examples/streamlit/**
  Prototype Streamlit app demonstrating keyword and URL highlighting using the shared core logic.

- **data/**  
  CSV/TTL/JSON-LD sources for building the document hierarchy knowledge graph.

## Quick Start

1. `pip install -r pyqt-pdf-analyzer/requirements.txt`  
2. `python pyqt-pdf-analyzer/main.py`  
3. File → Load Keywords / Load URL Validations  
4. File → Open PDF (load a UFC/UFGS spec)  
5. Toggle annotation categories in the sidebar

License: Public domain
