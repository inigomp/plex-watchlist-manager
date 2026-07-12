"""Obtención de la nota media de TMDB para un título."""
import logging
import urllib.parse

import requests

import config

logger = logging.getLogger(__name__)


def get_score(item_type, title, orig, year):
    """Devuelve la nota media de TMDB como string, o 'N/A' si no hay API key
    o no se encuentra el título. Prueba primero con el título original y, si no
    hay resultados, con el título traducido."""
    if not config.TMDB_API_KEY:
        return "N/A"

    search_type = "movie" if item_type == "movie" else "tv"
    query = orig or title
    if not query:
        return "N/A"

    try:
        results = _search(search_type, query, year)
        if not results and title:
            results = _search(search_type, title, year)
        if results:
            return str(round(results[0].get("vote_average", 0), 1))
    except Exception as e:
        logger.error(f"Error TMDB for {title}: {e}")

    return "N/A"


def _search(search_type, query, year):
    url = (
        f"https://api.themoviedb.org/3/search/{search_type}"
        f"?api_key={config.TMDB_API_KEY}&query={urllib.parse.quote(query)}&year={year}"
    )
    return requests.get(url, timeout=5).json().get("results", [])
