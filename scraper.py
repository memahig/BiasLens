# scraper.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import requests
import trafilatura

@dataclass
class ScrapeResult:
    url: str
    title: Optional[str]
    text: str
    success: bool
    error: Optional[str] = None

# These headers help convince the site you are a real person
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

def scrape_url(url: str) -> ScrapeResult:
    """
    Fetches article text. This is modular, so we can add 
    Proxies/Residential IPs here later without touching the main app.
    """
    try:
        # 1. Fetch the HTML
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
        
        # Check for the 403 Forbidden error specifically
        if r.status_code == 403:
            return ScrapeResult(url, None, "", False, "403 Forbidden: Site is blocking cloud access.")
        
        r.raise_for_status()
        
        # 2. Extract content using trafilatura
        downloaded = trafilatura.extract(r.text, output_format="txt", include_comments=False)
        
        if not downloaded or len(downloaded.strip()) < 200:
            return ScrapeResult(url, None, "", False, "Content too short or structure not recognized.")

        # 3. Extract Metadata for the title
        meta = trafilatura.extract_metadata(r.text)
        title = getattr(meta, "title", "Untitled Article")

        return ScrapeResult(url=url, title=title, text=downloaded.strip(), success=True)
    
    except Exception as e:
        return ScrapeResult(url=url, title=None, text="", success=False, error=str(e))