# PyQt PDF Document Analyzer

A professional desktop application for analyzing UFC/UFGS PDF documents with keyword highlighting and metadata extraction.

## Features

- **PDF Viewing**: Load and navigate PDF documents with zoom controls
- **Keyword Highlighting**: Highlight keywords by category with color coding
- **Category Management**: Enable/disable keyword categories dynamically
- **Metadata Analysis**: View page-level statistics and keyword analysis
- **Search Functionality**: Search and filter keywords
- **Professional UI**: Clean PyQt6 interface with resizable panels

## Installation

1. **Install Python 3.8+** (if not already installed)

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

## Usage

### Loading Documents
- Use **File → Open PDF** or **Ctrl+O** to load a PDF document
- The application will automatically extract text and analyze keywords

### Keyword Management
- Keywords are loaded from CSV files with columns: `keyword`, `category`, `color`
- Use **File → Load Keywords** to load custom keyword files
- Toggle categories on/off using checkboxes in the left panel
- View keyword statistics and legend

### Navigation
- Use navigation buttons or keyboard shortcuts:
  - **Previous Page**: ◀ button or toolbar
  - **Next Page**: ▶ button or toolbar
  - **Zoom In**: Ctrl++ or View menu
  - **Zoom Out**: Ctrl+- or View menu
  - **Fit to Width**: Ctrl+0 or View menu

### Keyword Categories

The application supports the following default keyword categories:

| Category | Color | Description |
|----------|-------|-------------|
| Required | Red | Mandatory requirements (shall) |
| Recommended | Orange | Recommended practices (should) |
| Prohibited | Black | Prohibited actions (not permitted) |
| Hazard | Blue | Safety hazards (flood, etc.) |
| Domain | Green | Technical domains (telecommunications, etc.) |

## File Structure

```
pyqt-pdf-analyzer/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── ui/                     # User interface components
│   ├── main_window.py     # Main application window
│   ├── pdf_viewer.py      # PDF viewer widget
│   └── keyword_panel.py   # Keyword management panel
└── README.md              # This file

src/
└── core/                   # Shared functionality
    ├── config.py          # Configuration settings
    ├── keyword_manager.py # Keyword loading and management
    └── pdf_processor.py   # PDF processing and highlighting
```

## Configuration

The application looks for default files in the repository:
- Keywords: `examples/streamlit/keywords.csv`
- Metadata: `examples/streamlit/data/deontic_metadata.csv`
- Sample PDF: `examples/streamlit/data/ufc_example.pdf`

You can customize these paths in `core/config.py`.

## Dependencies

- **PyQt6**: Modern GUI framework
- **PyMuPDF**: PDF processing and rendering
- **pandas**: Data manipulation for CSV files
- **Pillow**: Image processing for highlighting

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open PDF |
| Ctrl+Q | Quit application |
| Ctrl++ | Zoom in |
| Ctrl+- | Zoom out |
| Ctrl+0 | Fit to width |

## Troubleshooting

### Common Issues

1. **"No module named 'PyQt6'"**
   - Install PyQt6: `pip install PyQt6`

2. **"Could not load default keywords"**
   - Ensure `keywords.csv` exists in the expected location
   - Use **File → Load Keywords** to load from a different location

3. **PDF rendering issues**
   - Ensure PyMuPDF is installed: `pip install PyMuPDF`
   - Try reducing zoom level for large documents

### Performance Tips

- Large PDFs may take time to process initially
- Disable unused keyword categories to improve rendering speed
- Use "Fit to Width" for optimal viewing on different screen sizes

## Development

### Adding New Features

1. **New keyword categories**: Update `keywords.csv` and `Config.KEYWORD_COLORS`
2. **Custom highlighting**: Modify `PDFProcessor._apply_keyword_highlighting()`
3. **Additional metadata**: Extend `PageMetadata` class and processing logic

### Code Structure

- **Core modules**: Business logic and data processing
- **UI modules**: PyQt6 widgets and user interface
- **Signal-slot pattern**: Used for component communication
- **Threading**: PDF rendering runs in background threads

## License

This project is part of the Criteria Assistant suite and follows the same licensing terms.
