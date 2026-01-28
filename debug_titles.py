from plex_api import PlexAPI
import json

PLEX_TOKEN = "T8ibaxz7N8Us9toUkHbu"
plex = PlexAPI(PLEX_TOKEN)
watchlist = plex.get_watchlist()

if watchlist:
    # Miramos los primeros elementos para ver qué campos traen los títulos
    for i in range(min(3, len(watchlist))):
        item = watchlist[i]
        print(f"--- Item {i} ---")
        print(f"Title: {item.get('title')}")
        print(f"Original Title: {item.get('originalTitle')}")
        # Buscamos si hay algo relacionado con 'Spanish' o 'es'
        for k, v in item.items():
            if 'title' in k.lower():
                print(f"{k}: {v}")
else:
    print("No se pudo obtener la watchlist")
