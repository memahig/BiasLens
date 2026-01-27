from __future__ import annotations

from typing import Optional, Tuple

from scraper_adapter import try_scrape


def load_text_from_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def resolve_input_text(
    url: Optional[str],
    file_path: Optional[str],
    text_arg: Optional[str],
) -> Tuple[str, str, Optional[str]]:
    """
    Returns: (text, source_title, source_url)
    """
    if url:
        sr = try_scrape(url)
        if not sr.success:
            raise RuntimeError(sr.text)
        return sr.text or "", "scraped_url", url

    if file_path:
        return load_text_from_file(file_path), file_path, None

    if text_arg is not None:
        return text_arg, "manual_text", None

    return "", "none", None
