from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScrapeResult:
    text: str
    success: bool


def try_scrape(url: str) -> ScrapeResult:
    """
    Uses scraper.py if present. Fails safely with a user-readable message.
    """
    try:
        import scraper  # type: ignore

        if hasattr(scraper, "scrape_url"):
            res = scraper.scrape_url(url)  # expected ScrapeResult-like object
            text = getattr(res, "text", "")
            success = bool(getattr(res, "success", False))
            return ScrapeResult(text=text, success=success)

        return ScrapeResult(
            text="scraper.py is present but does not define scrape_url(url).",
            success=False,
        )
    except Exception as e:
        return ScrapeResult(text=f"Scrape exception: {e}", success=False)
