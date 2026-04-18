from __future__ import annotations

from urllib.parse import urlparse


BLOCKED_DOMAINS = {
    "globalresearch.ca",
    "www.globalresearch.ca",
    "wnd.com",
    "www.wnd.com",
}

TRUSTED_DOMAINS = {
    "abcnews.go.com",
    "abcnews.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "bloomberg.com",
    "foreignpolicy.com",
    "ft.com",
    "newyorker.com",
    "nytimes.com",
    "reuters.com",
    "theguardian.com",
    "washingtonpost.com",
}

DOWNRANKED_DOMAINS = {
    "antiwar.com",
    "economictimes.indiatimes.com",
    "financialpost.com",
    "timesofindia.indiatimes.com",
}


def source_quality_score(url: str) -> float:
    domain = urlparse(url).netloc.lower()
    if domain in BLOCKED_DOMAINS:
        return -1.0
    if domain in TRUSTED_DOMAINS:
        return 0.12
    if domain in DOWNRANKED_DOMAINS:
        return -0.05
    return 0.0


def is_source_allowed(url: str) -> bool:
    return source_quality_score(url) > -1.0
