from dataclasses import dataclass

@dataclass
class AnnotationSummary:
    """
    Summary counts of annotations found on a page.
    """
    total: int       # Total number of annotations
    keywords: int    # Number of keyword annotations
    urls: int        # Number of URL validation annotations
