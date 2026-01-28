import os
import threading
import urllib.parse
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
from plex_api import PlexAPI

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# --- Configuración ---
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
SERVER_NAME = os.getenv("SERVER_NAME", "Navidad")
MONGO_URI = os.getenv("MONGO_URI") # URI de MongoDB Atlas
TMDB_API_KEY = os.getenv("TMDB_API_KEY") # API Key de TMDB

# Conexión a MongoDB
client = MongoClient(MONGO_URI)
db = client['plex_manager']
collection = db['watchlist']

def sync_watchlist():
    """Tarea en segundo plano que sincroniza Plex con MongoDB."""
    logger.info("Iniciando sincronización con Plex...")
    try:
        plex = PlexAPI(PLEX_TOKEN)
        
        # 1. Obtener Watchlist de Plex
        watchlist_raw = plex.get_watchlist()
        watchlist_final = []
        
        # 2. Obtener librerías del servidor para cruce
        libraries = plex.get_server_libraries(SERVER_NAME)
        server_items = []
        if libraries:
            for lib in libraries:
                lib_items = plex.get_library_items(lib)
                for item in lib_items:
                    server_items.append({
                        "title": item.get("title", "").lower(),
                        "orig": item.get("originalTitle", "").lower(),
                        "lib": lib["title"],
                        "added_at": int(item.get("addedAt", 0))
                    })

        # 3. Procesar y Cruzar
        for item in watchlist_raw:
            title = item.get("title")
            orig = item.get("originalTitle")
            year = item.get("year")
            type_ = "Película" if item.get("type") == "movie" else "Serie"
            thumb = item.get("thumb")
            
            image_url = thumb if thumb and thumb.startswith('http') else None
            if not image_url and thumb:
                image_url = f"https://metadata.provider.plex.tv{thumb}?X-Plex-Token={PLEX_TOKEN}"
            
            keys = {title.lower()}
            if orig: keys.add(orig.lower())
            
            # Verificar disponibilidad
            on_server = False
            found_in_libs = []
            added_at = 0
            for s_item in server_items:
                if s_item["title"] in keys or (s_item["orig"] and s_item["orig"] in keys):
                    on_server = True
                    added_at = s_item["added_at"]
                    if s_item["lib"] not in found_in_libs:
                        found_in_libs.append(s_item["lib"])
            
            # 4. Obtener nota de TMDB (Opcional si hay API Key)
            tmdb_score = "N/A"
            if TMDB_API_KEY:
                try:
                    search_type = "movie" if item.get("type") == "movie" else "tv"
                    tmdb_url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={TMDB_API_KEY}&query={urllib.parse.quote(title or orig)}&year={year}"
                    import requests
                    tmdb_res = requests.get(tmdb_url, timeout=5).json()
                    if tmdb_res.get("results"):
                        tmdb_score = str(round(tmdb_res["results"][0].get("vote_average", 0), 1))
                except Exception as e:
                    logger.error(f"Error buscando en TMDB para {title}: {e}")

            watchlist_final.append({
                "plex_id": item.get("ratingKey"),
                "title": title,
                "orig": orig,
                "year": year,
                "type": type_,
                "image": image_url,
                "url": f"https://www.filmaffinity.com/es/search.php?stext={title.replace(' ', '+')}",
                "on_server": on_server,
                "libraries": found_in_libs,
                "score": tmdb_score,
                "added_at": added_at
            })

        # 4. Guardar en MongoDB (Update or Insert)
        if watchlist_final:
            # Opción simple: Limpiar y reinsertar (para mantener sincronía total)
            collection.delete_many({})
            collection.insert_many(watchlist_final)
            logger.info(f"Sincronización completada: {len(watchlist_final)} elementos.")
        
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")

# Configurar el planificador (cada hora)
scheduler = BackgroundScheduler()
scheduler.add_job(func=sync_watchlist, trigger="interval", hours=1)
scheduler.start()

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    # Lee directamente de la base de datos (instantáneo)
    data = list(collection.find({}, {'_id': 0}))
    return jsonify(data)

import threading

def force_sync_worker():
    """Ejecuta la sincronización en un hilo separado."""
    with app.app_context():
        sync_watchlist()

@app.route('/api/sync', methods=['GET', 'POST'])
def force_sync():
    # Verificación de seguridad rápida
    if not PLEX_TOKEN or not MONGO_URI:
        return jsonify({"error": "Configuración incompleta (Tokens/Mongo)"}), 500
        
    # Lanzamos la sincronización en segundo plano para evitar el timeout de 30s de Render
    thread = threading.Thread(target=force_sync_worker)
    thread.start()
    
    return jsonify({
        "status": "sync_initiated",
        "message": "La sincronización ha comenzado en segundo plano. Los datos aparecerán en unos momentos."
    })

if __name__ == '__main__':
    # Ejecutar sincronización inicial al arrancar
    # sync_watchlist() 
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
