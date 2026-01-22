import trafilatura


class ScrapeResult:
    def __init__(self, text: str, success: bool):
        self.text = text
        self.success = success


def scrape_url(url: str) -> ScrapeResult:
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
