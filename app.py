import os
import json
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from plex_api import PlexAPI
from fa_scraper import FAScraper

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Configuración ---
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
SERVER_NAME = os.getenv("SERVER_NAME", "Navidad")
# ---------------------

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist_data():
    plex = PlexAPI(PLEX_TOKEN)
    
    # 1. Obtener Watchlist
    watchlist_raw = plex.get_watchlist()
    watchlist = [] 
    
    # En el backend de la web, por ahora no usaremos el scraper en cada petición 
    # para evitar bloqueos y lentitud. Devolveremos el enlace de búsqueda.
    for item in watchlist_raw:
        title = item.get("title")
        orig = item.get("originalTitle")
        year = item.get("year")
        type_ = "Película" if item.get("type") == "movie" else "Serie"
        thumb = item.get("thumb")
        
        # Las imágenes de Discover suelen ser URLs completas ahora
        if thumb and thumb.startswith('http'):
            image_url = thumb
        elif thumb:
            image_url = f"https://metadata.provider.plex.tv{thumb}?X-Plex-Token={PLEX_TOKEN}"
        else:
            image_url = None
        
        keys = {title.lower()}
        if orig: keys.add(orig.lower())
        
        watchlist.append({
            "title": title,
            "orig": orig,
            "year": year,
            "type": type_,
            "keys": list(keys),
            "image": image_url,
            "url": f"https://www.filmaffinity.com/es/search.php?stext={title.replace(' ', '+')}",
            "on_server": False,
            "libraries": []
        })

    # 2. Buscar en el Servidor
    libraries = plex.get_server_libraries(SERVER_NAME)
    if libraries:
        for lib in libraries:
            items = plex.get_library_items(lib)
            for srv_item in items:
                srv_title = srv_item.get("title", "").lower()
                srv_orig = srv_item.get("originalTitle", "").lower()
                
                for meta in watchlist:
                    if srv_title in meta["keys"] or (srv_orig and srv_orig in meta["keys"]):
                        meta["on_server"] = True
                        if lib["title"] not in meta["libraries"]:
                            meta["libraries"].append(lib["title"])

    return jsonify(watchlist)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
