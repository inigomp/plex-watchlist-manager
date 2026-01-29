from plex_api import PlexAPI
import os
from dotenv import load_dotenv
import json
import xml.etree.ElementTree as ET

# Cargar entorno
load_dotenv()
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
SERVER_NAME = os.getenv("SERVER_NAME")

if not PLEX_TOKEN:
    print("Error: PLEX_TOKEN no encontrado en .env")
    exit()

print(f"Token: {PLEX_TOKEN[:5]}... SERVER: {SERVER_NAME}")

plex = PlexAPI(PLEX_TOKEN)

# 1. Obtener Watchlist
print("\n--- WATCHLIST (JSON) ---")
try:
    watchlist = plex.get_watchlist()
    print(f"Total en Watchlist: {len(watchlist)}")
    # Buscar 'Anaconda' o 'La cena' o mostrar los primeros 3
    target_titles = ["anaconda", "la cena"]
    found_targets = []
    
    for item in watchlist:
        title = item.get('title', '').lower()
        if any(t in title for t in target_titles):
            found_targets.append(item)
            
    # Si no encontramos los targets, mostramos los primeros 3
    display_items = found_targets if found_targets else watchlist[:3]
    
    for item in display_items:
        print(f"Title: {item.get('title')} ({item.get('year')})")
        print(f"  ratingKey: {item.get('ratingKey')}")
        print(f"  guid: {item.get('guid')}")
        print(f"  type: {item.get('type')}")
        if 'Guid' in item:
             print(f"  External Guids: {item.get('Guid')}")
        print("-" * 20)

except Exception as e:
    print(f"Error obteniendo Watchlist: {e}")

# 2. Obtener Server Items
print("\n--- SERVER ITEMS (XML) ---")
try:
    libraries = plex.get_server_libraries(SERVER_NAME)
    if not libraries:
        print(f"No se encontraron librerías para el servidor: {SERVER_NAME}")
    else:
        for lib in libraries:
            print(f"Librería: {lib['title']}")
            items = plex.get_library_items(lib)
            print(f"  Total items: {len(items)}")
            
            # Buscar coincidencia visual
            count = 0
            for item in items:
                title = item.get("title", "")
                year = item.get("year", "")
                guid = item.get("guid", "")
                ratingKey = item.get("ratingKey", "")
                
                # Mostrar si se parece a los targets o los primeros 3
                if any(t in title.lower() for t in target_titles) or count < 3:
                     print(f"  Title: {title} ({year})")
                     print(f"    guid: {guid}")
                     print(f"    ratingKey: {ratingKey}")
                     count += 1
except Exception as e:
    print(f"Error obteniendo Server items: {e}")
