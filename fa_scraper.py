import urllib.parse
from playwright.sync_api import sync_playwright

class FAScraper:
    def __init__(self):
        self.base_url = "https://www.filmaffinity.com/es/main.html"
        self._browser = None
        self._context = None
        self._playwright = None
        self._page = None

    def __enter__(self):
        self._playwright = sync_playwright().start()
        # Using a newer Chromium version and setting a realistic viewport
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        self._page = self._context.new_page()
        # Add a realistic header
        self._page.set_extra_http_headers({"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def get_info(self, title):
        """Searches for a movie/series and returns its FilmAffinity score and URL."""
        if not self._page:
            return "N/A", "N/A"

        try:
            search_url = f"https://www.filmaffinity.com/es/search.php?stext={urllib.parse.quote(title)}"
            self._page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            
            # 1. Direct hit?
            rating_div = self._page.query_selector("#movie-rat-avg")
            if rating_div:
                score = rating_div.inner_text().strip().replace(",", ".")
                return score, self._page.url
            
            # 2. Search results?
            if "search.php" in self._page.url:
                results = self._page.query_selector_all(".se-it")
                if results:
                    all_links = results[0].query_selector_all("a")
                    for link in all_links:
                        href = link.get_attribute("href")
                        if href and "/film" in href:
                            if not href.startswith("http"):
                                href = "https://www.filmaffinity.com" + href
                            
                            # We found the link! 
                            # We can try to get the rating if it's visible in the search item
                            rating_in_result = results[0].query_selector(".avgrat-box") or \
                                               results[0].query_selector(".rat-avg")
                            
                            score = "N/A"
                            if rating_in_result:
                                txt = rating_in_result.inner_text().strip().replace(",", ".")
                                if txt and txt[0].isdigit():
                                    score = txt
                            
                            return score, href
            
        except Exception:
            pass
            
        return "N/A", f"https://www.filmaffinity.com/es/search.php?stext={urllib.parse.quote(title)}"
