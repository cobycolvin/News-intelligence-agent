import re


def clean_article_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    boilerplate_patterns = [r"subscribe now", r"all rights reserved", r"cookie policy"]
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()
