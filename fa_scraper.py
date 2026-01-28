import requests
from bs4 import BeautifulSoup
import urllib.parse

class FAScraper:
    def __init__(self):
        self.base_url = "https://www.filmaffinity.com/es/search.php?stext="
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def get_score(self, title):
        """Searches for a movie/series and returns its FilmAffinity score."""
        try:
            search_url = self.base_url + urllib.parse.quote(title)
            resp = requests.get(search_url, headers=self.headers, timeout=10)
            if resp.status_code != 200: return None
            
            soup = BeautifulSoup(resp.content, "html.parser")
            
            # If search redirected to a movie page
            rating_div = soup.find("div", {"id": "movie-rat-avg"})
            if rating_div:
                return rating_div.get_text().strip()
            
            # If search returned multiple results, pick the first one
            first_result = soup.find("div", {"class": "mc-title"})
            if first_result:
                link = first_result.find("a")["href"]
                movie_resp = requests.get(link, headers=self.headers, timeout=10)
                movie_soup = BeautifulSoup(movie_resp.content, "html.parser")
                rating_div = movie_soup.find("div", {"id": "movie-rat-avg"})
                return rating_div.get_text().strip() if rating_div else "N/A"
                
        except Exception as e:
            print(f"Error scraping FA for {title}: {e}")
            
        return "N/A"
