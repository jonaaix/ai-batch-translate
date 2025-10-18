# File: ai_translator/utils.py
from typing import Any, Dict, Optional, Tuple

# Language priority for finding a source text
SOURCE_LANG_PRIORITY = ["de", "en", "fr"]


def is_language_key(key: str) -> bool:
    """Check if a key is a 2-letter language code."""
    return len(key) == 2


def get_source_language(item: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Finds the best available source language based on priority."""
    for lang in SOURCE_LANG_PRIORITY:
        if item.get(lang) and is_language_key(lang):
            return lang, item[lang]
    for lang, text in item.items():
        if is_language_key(lang) and text:
            return lang, text
    return None