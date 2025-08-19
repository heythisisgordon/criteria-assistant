"""
Configuration management for the PDF analyzer.
"""

import os
from typing import Dict, Any

class Config:
    """Application configuration settings."""
    
    # Default paths
    DEFAULT_KEYWORDS_PATH = "../streamlit-test/keywords.csv"
    DEFAULT_METADATA_PATH = "../streamlit-test/data/deontic_metadata.csv"
    DEFAULT_PDF_PATH = "../streamlit-test/data/ufc_example.pdf"
    
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
    
    # Keyword highlighting colors (matching streamlit app)
    KEYWORD_COLORS = {
        "Required": "#FF0000",      # red
        "Recommended": "#FFA500",   # orange  
        "Prohibited": "#000000",    # black
        "Hazard": "#0000FF",        # blue
        "Domain": "#008000"         # green
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
