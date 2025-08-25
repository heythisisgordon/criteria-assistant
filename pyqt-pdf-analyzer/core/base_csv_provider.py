import logging
from typing import List, Set

import pandas as pd

from core.annotation_system import AnnotationProvider

logger = logging.getLogger(__name__)

class BaseCSVAnnotationProvider(AnnotationProvider):
    """Base class for annotation providers backed by CSV data."""

    required_columns: List[str] = []
    category_column: str = "category"

    def __init__(self) -> None:
        self.data_df: pd.DataFrame = pd.DataFrame()
        self.enabled_categories: Set[str] = set()

    def get_default_source_path(self) -> str:
        """Get default path for CSV source."""
        raise NotImplementedError

    def _post_load(self) -> None:
        """Hook for subclasses to process data after loading."""
        pass

    def load_data(self, source_path: str = None) -> bool:
        """Load annotation data from CSV file."""
        if source_path is None:
            source_path = self.get_default_source_path()
        logger.debug(f"Loading annotation data from: {source_path}")
        try:
            self.data_df = pd.read_csv(source_path)
            logger.debug(f"DataFrame loaded with shape: {self.data_df.shape}")
            if not all(col in self.data_df.columns for col in self.required_columns):
                raise ValueError(f"CSV must contain columns: {self.required_columns}")
            self.enabled_categories = set(self.data_df[self.category_column].unique())
            self._post_load()
            logger.debug("Annotation data load successful")
            return True
        except (FileNotFoundError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as e:
            logger.exception("Error loading data from %s: %s", source_path, e)
            return False

    def get_categories(self) -> Set[str]:
        """Get all categories present in the data."""
        return set(self.data_df[self.category_column].unique()) if not self.data_df.empty else set()

    def get_enabled_categories(self) -> Set[str]:
        """Get currently enabled categories."""
        return self.enabled_categories.copy()

    def set_category_enabled(self, category: str, enabled: bool) -> None:
        """Enable or disable a category."""
        if enabled:
            self.enabled_categories.add(category)
        else:
            self.enabled_categories.discard(category)
