"""
Keyword and URL validation management for PDF analysis.
Handles loading, filtering, and categorizing keywords and URL validations from CSV files.
"""

import logging
import pandas as pd
import re
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass

from core.config import Config
from core.url_utils import COMPILED_URL_PATTERNS

logger = logging.getLogger(__name__)

@dataclass
class Keyword:
    """Represents a keyword with its category and color."""
    text: str
    category: str
    color: str
    
    def __post_init__(self):
        """Normalize keyword text to lowercase for matching."""
        self.text = self.text.lower()

@dataclass
class URLValidation:
    """Represents a URL with its validation status."""
    url: str
    status: str
    response_code: Optional[int]
    final_url: str
    error_message: Optional[str]
    is_wbdg: bool
    check_certainty: str
    color: str
    
    def __post_init__(self):
        """Set color based on status."""
        self.color = Config.get_color_for_status(self.status)

class KeywordManager:
    """Manages keyword and URL validation loading, filtering, and categorization."""
    
    def __init__(self):
        """Initialize the keyword and URL validation manager."""
        # Keyword functionality
        self.keywords: List[Keyword] = []
        self.categories: Set[str] = set()
        self.enabled_categories: Set[str] = set()
        self._keyword_map: Dict[str, Keyword] = {}
        
        # URL validation functionality
        self.url_validations: List[URLValidation] = []
        self.url_statuses: Set[str] = set()
        self.enabled_url_statuses: Set[str] = set()
        self._url_lookup: Dict[str, URLValidation] = {}
        
        # URL detection patterns

        self.url_patterns = [
            r'https?://[^\s<>"{}|\\^`\[\]]+',  # Standard HTTP/HTTPS
            r'www\.[^\s<>"{}|\\^`\[\]]+',      # www. domains
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?',  # domain.com
            r'mailto:[^\s<>"{}|\\^`\[\]]+'     # Email addresses
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.url_patterns]

    def _load_records(
        self,
        csv_path: str,
        required_cols: List[str],
        factory: Callable[[pd.Series], Any],
    ) -> Optional[List[Any]]:
        """Generic CSV loader validating columns and building objects."""
        try:
            df = pd.read_csv(csv_path)
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            return [factory(row) for _, row in df.iterrows()]
        except (FileNotFoundError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
            logger.exception("Error loading records from %s: %s", csv_path, e)
            return None
        
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

        records = self._load_records(
            csv_path,
            ['keyword', 'category', 'color'],
            lambda row: Keyword(
                text=str(row['keyword']),
                category=str(row['category']),
                color=str(row['color']),
            ),
        )

        if records is None:
            return False

        # Clear existing data
        self.keywords = records
        self.categories = {kw.category for kw in self.keywords}
        self._keyword_map = {kw.text: kw for kw in self.keywords}

        # Enable all categories by default
        self.enabled_categories = self.categories.copy()

        return True
    
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
    
    # URL Validation Methods
    
    def load_url_validations(self, csv_path: str = None) -> bool:
        """
        Load URL validation data from CSV file.
        
        Args:
            csv_path: Path to URL validation CSV file. Uses default if None.
            
        Returns:
            True if successful, False otherwise.
        """
        if csv_path is None:
            csv_path = Config.get_url_validation_path()

        records = self._load_records(
            csv_path,
            ['url', 'status', 'response_code', 'final_url', 'is_wbdg', 'check_certainty'],
            lambda row: URLValidation(
                url=str(row['url']),
                status=str(row['status']),
                response_code=int(row['response_code']) if pd.notna(row['response_code']) else None,
                final_url=str(row['final_url']),
                error_message=str(row['error_message']) if pd.notna(row['error_message']) else None,
                is_wbdg=bool(row['is_wbdg']),
                check_certainty=str(row['check_certainty']),
                color="",  # Will be set in __post_init__
            ),
        )

        if records is None:
            return False

        # Clear existing data
        self.url_validations = records
        self.url_statuses = {v.status for v in self.url_validations}
        self._url_lookup = {v.url: v for v in self.url_validations}

        # Enable all statuses by default
        self.enabled_url_statuses = self.url_statuses.copy()

        return True
    
    def get_url_statuses(self) -> List[str]:
        """Get all available URL status categories."""
        return sorted(list(self.url_statuses))
    
    def get_url_categories(self) -> List[str]:
        """Alias for get_url_statuses, matching API for URL categories."""
        return self.get_url_statuses()
    
    def get_urls_for_status(self, status: str) -> List[URLValidation]:
        """Get all URLs for a specific status."""
        return [url for url in self.url_validations if url.status == status]
    
    def is_url_status_enabled(self, status: str) -> bool:
        """Check if a URL status is currently enabled."""
        return status in self.enabled_url_statuses
    
    def enable_url_status(self, status: str, enabled: bool = True):
        """Enable or disable a URL status category."""
        if enabled:
            self.enabled_url_statuses.add(status)
        else:
            self.enabled_url_statuses.discard(status)
    
    def toggle_url_status(self, status: str):
        """Toggle the enabled state of a URL status."""
        if status in self.enabled_url_statuses:
            self.enabled_url_statuses.remove(status)
        else:
            self.enabled_url_statuses.add(status)
    
    def find_urls_in_text(self, text: str) -> List[URLValidation]:
        """
        Find all enabled URL validations present in the given text.
        
        Args:
            text: Text to search for URLs.
            
        Returns:
            List of URL validations found in the text.
        """
        if not text:
            return []
        
        found_urls = []
        
        # Find all URL matches in text
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                url_text = match.group().strip()
                
                # Clean up common artifacts
                url_text = re.sub(r'<[^>]+>', '', url_text)  # Remove XML tags
                url_text = url_text.rstrip('.,;:!?')  # Remove trailing punctuation
                
                # Look up validation data
                validation = self._url_lookup.get(url_text)
                if validation and validation.status in self.enabled_url_statuses:
                    found_urls.append(validation)
        
        return found_urls
    
    def get_url_stats(self) -> Dict[str, int]:
        """Get statistics about loaded URL validations by status."""
        stats = {}
        for status in self.url_statuses:
            stats[status] = len(self.get_urls_for_status(status))
        return stats
