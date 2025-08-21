"""
Configuration management for the PDF analyzer.
"""

import os
from typing import Dict, Any

class Config:
    """Application configuration settings."""
    
    # Default paths
    DEFAULT_KEYWORDS_PATH = "examples/streamlit/keywords.csv"
    DEFAULT_METADATA_PATH = "examples/streamlit/data/deontic_metadata.csv"
    DEFAULT_PDF_PATH = "examples/streamlit/data/ufc_example.pdf"
    DEFAULT_URL_VALIDATION_PATH = "examples/streamlit/data/url_validation_results.csv"
    
    # UI Settings
    DEFAULT_WINDOW_WIDTH = 1200
    DEFAULT_WINDOW_HEIGHT = 800
    DEFAULT_ZOOM_LEVEL = 1.0
    MIN_ZOOM = 0.25
    MAX_ZOOM = 5.0
    ZOOM_STEP = 0.25
    
    # PDF Rendering
    DEFAULT_DPI = 150
    HIGH_DPI = 300

    # Annotation cache size to bound memory usage
    ANNOTATION_CACHE_SIZE = 1000
    
    # Keyword highlighting colors (matching streamlit app)
    KEYWORD_COLORS = {
        "Required": "#FF0000",      # red
        "Recommended": "#FFA500",   # orange  
        "Prohibited": "#000000",    # black
        "Hazard": "#0000FF",        # blue
        "Domain": "#008000"         # green
    }
    
    # URL validation colors (matching notebook analysis)
    URL_STATUS_COLORS = {
        "PASS": "#00AA00",                    # Green
        "FAIL": "#CC0000",                    # Red  
        "WARN_WBDG_CONTENT_ERROR": "#FF8800", # Orange
        "EMAIL": "#0066CC",                   # Blue
        "INVALID": "#808080",                 # Gray
        "PROCESSING_ERROR": "#404040",        # Dark Gray
        "BATCH_MISSING_RESULT": "#666666",    # Medium Gray
        "NOT_MAPPED": "#999999"               # Light Gray
    }
    
    # UI Colors
    HIGHLIGHT_OPACITY = 0.3
    SELECTION_COLOR = "#3399FF"
    BACKGROUND_COLOR = "#F5F5F5"
    
    @classmethod
    def get_keywords_path(cls) -> str:
        """Get the path to the keywords CSV file."""
        return os.path.abspath(cls.DEFAULT_KEYWORDS_PATH)
    
    @classmethod
    def get_metadata_path(cls) -> str:
        """Get the path to the metadata CSV file."""
        return os.path.abspath(cls.DEFAULT_METADATA_PATH)
    
    @classmethod
    def get_default_pdf_path(cls) -> str:
        """Get the path to the default PDF file."""
        return os.path.abspath(cls.DEFAULT_PDF_PATH)
    
    @classmethod
    def get_color_for_category(cls, category: str) -> str:
        """Get the highlight color for a keyword category."""
        return cls.KEYWORD_COLORS.get(category, "#808080")  # Default gray
    
    @classmethod
    def get_url_validation_path(cls) -> str:
        """Get the path to the URL validation CSV file."""
        return os.path.abspath(cls.DEFAULT_URL_VALIDATION_PATH)
    
    @classmethod
    def get_color_for_status(cls, status: str) -> str:
        """Get the highlight color for a URL status."""
        return cls.URL_STATUS_COLORS.get(status, "#808080")  # Default gray
