import trafilatura
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError


class ScrapeResult:
    def __init__(self, text: str, success: bool):
        self.text = text
        self.success = success


def _scrape_worker(url: str) -> ScrapeResult:
    """
    Runs in a separate process so we can enforce a hard timeout.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ScrapeResult("Could not download URL (possibly blocked or requires JS/login).", False)

        text = trafilatura.extract(downloaded)
        if text and text.strip():
            return ScrapeResult(text.strip(), True)

        return ScrapeResult("Downloaded page but could not extract readable article text.", False)

    except Exception as e:
        return ScrapeResult(f"Scrape exception: {e}", False)


def scrape_url(url: str) -> ScrapeResult:
    """
    Hard-timeout protected scrape.
    This function MUST NOT hang.
    """
    try:
        with ProcessPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_scrape_worker, url)
            return fut.result(timeout=25)
    except FuturesTimeoutError:
        return ScrapeResult("SCRAPE_TIMEOUT: scraper exceeded 25s (likely blocked / bot-challenge / slow network).", False)
    except Exception as e:
        return ScrapeResult(f"Scrape exception: {e}", False)
