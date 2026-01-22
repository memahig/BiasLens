import trafilatura

class ScrapeResult:
    def __init__(self, text, success):
        self.text = text
        self.success = success

def scrape_url(url):
    try:
        # Trafilatura handles the request and the cleaning in one go
        downloaded = trafilatura.fetch_url(url)
        # extract() removes the "junk" like navbars and ads
        text = trafilatura.extract(downloaded)
        
        if text:
            return ScrapeResult(text, True)
        else:
            return ScrapeResult("Could not extract text from this URL.", False)
    except Exception as e:
        return ScrapeResult(str(e), False)