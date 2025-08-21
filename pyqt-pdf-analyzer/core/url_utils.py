import re

# Common URL detection patterns used across the application.
URL_PATTERNS = [
    r'https?://[^\s<>"{}|\^`\[\]]+',
    r'www\.[^\s<>"{}|\^`\[\]]+',
    r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\^`\[\]]*)?',
    r'mailto:[^\s<>"{}|\^`\[\]]+'
]

COMPILED_URL_PATTERNS = [re.compile(p, re.IGNORECASE) for p in URL_PATTERNS]
