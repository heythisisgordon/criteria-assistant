"""
Keyword management for PDF analysis.
Handles loading, filtering, and categorizing keywords from CSV files.
"""

import pandas as pd
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from core.config import Config

@dataclass
class Keyword:
    """Represents a keyword with its category and color."""
    text: str
    category: str
    color: str
    
    def __post_init__(self):
        """Normalize keyword text to lowercase for matching."""
        self.text = self.text.lower()

class KeywordManager:
    """Manages keyword loading, filtering, and categorization."""
    
    def __init__(self):
        """Initialize the keyword manager."""
        self.keywords: List[Keyword] = []
        self.categories: Set[str] = set()
        self.enabled_categories: Set[str] = set()
        self._keyword_map: Dict[str, Keyword] = {}
        
    def load_keywords(self, csv_path: str = None) -> bool:
        """
        Load keywords from CSV file.
        
        Args:
            csv_path: Path to keywords CSV file. Uses default if None.
            
        Returns:
            True if successful, False otherwise.
        """
        if csv_path is None:
            csv_path = Config.get_keywords_path()
            
        try:
            df = pd.read_csv(csv_path)
            
            # Validate required columns
            required_cols = ['keyword', 'category', 'color']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            
            # Clear existing data
            self.keywords.clear()
            self.categories.clear()
            self._keyword_map.clear()
            
            # Load keywords
            for _, row in df.iterrows():
                keyword = Keyword(
                    text=str(row['keyword']),
                    category=str(row['category']),
                    color=str(row['color'])
                )
                
                self.keywords.append(keyword)
                self.categories.add(keyword.category)
                self._keyword_map[keyword.text] = keyword
            
            # Enable all categories by default
            self.enabled_categories = self.categories.copy()
            
            return True
            
        except Exception as e:
            print(f"Error loading keywords: {e}")
            return False
    
    def get_categories(self) -> List[str]:
        """Get all available keyword categories."""
        return sorted(list(self.categories))
    
    def get_keywords_for_category(self, category: str) -> List[Keyword]:
        """Get all keywords for a specific category."""
        return [kw for kw in self.keywords if kw.category == category]
    
    def is_category_enabled(self, category: str) -> bool:
        """Check if a category is currently enabled."""
        return category in self.enabled_categories
    
    def enable_category(self, category: str, enabled: bool = True):
        """Enable or disable a keyword category."""
        if enabled:
            self.enabled_categories.add(category)
        else:
            self.enabled_categories.discard(category)
    
    def toggle_category(self, category: str):
        """Toggle the enabled state of a category."""
        if category in self.enabled_categories:
            self.enabled_categories.remove(category)
        else:
            self.enabled_categories.add(category)
    
    def find_keywords_in_text(self, text: str) -> List[Keyword]:
        """
        Find all enabled keywords present in the given text.
        
        Args:
            text: Text to search for keywords.
            
        Returns:
            List of keywords found in the text.
        """
        if not text:
            return []
            
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.keywords:
            # Only check enabled categories
            if keyword.category not in self.enabled_categories:
                continue
                
            if keyword.text in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def get_keyword_stats(self) -> Dict[str, int]:
        """Get statistics about loaded keywords by category."""
        stats = {}
        for category in self.categories:
            stats[category] = len(self.get_keywords_for_category(category))
        return stats
    
    def search_keywords(self, search_term: str) -> List[Keyword]:
        """
        Search for keywords containing the search term.
        
        Args:
            search_term: Term to search for in keyword text.
            
        Returns:
            List of matching keywords.
        """
        if not search_term:
            return self.keywords.copy()
            
        search_lower = search_term.lower()
        return [kw for kw in self.keywords if search_lower in kw.text]
