import os
import threading
import urllib.parse
import logging
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
from plex_api import PlexAPI

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

PORT = int(os.getenv("PORT", 5000))

# --- Configuración ---
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
SERVER_NAME = os.getenv("SERVER_NAME", "Navidad")
MONGO_URI = os.getenv("MONGO_URI") # URI de MongoDB Atlas
TMDB_API_KEY = os.getenv("TMDB_API_KEY") # API Key de TMDB
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Conexión a MongoDB
client = MongoClient(MONGO_URI)
db = client['plex_manager']
collection = db['watchlist']

def send_telegram_notification(item):
    """Envía un mensaje a Telegram avisando de que hay contenido nuevo disponible."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
        
    msg = f"🍿 *¡Nuevo en tu Plex!*\n\n"
    msg += f"🎬 *{item['title']}* ({item['year']})\n"
    msg += f"📁 Tipo: {item['type']}\n"
    msg += f"📍 Disponible en: {', '.join(item['libraries'])}\n\n"
    msg += f"[Ver en FilmAffinity]({item['url']})"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
        logger.info(f"Notificación de Telegram enviada para: {item['title']}")
    except Exception as e:
        logger.error(f"Error enviando Telegram: {e}")

def sync_watchlist():
    """Tarea en segundo plano que sincroniza Plex con MongoDB. Resistente a fallos de conexión."""
    logger.info("Iniciando sincronización resiliente...")
    try:
        plex = PlexAPI(PLEX_TOKEN)
        
        # 0. Obtener estado anterior para detectar novedades
        old_data = {}
        try:
            old_data = {item['plex_id']: item['on_server'] for item in collection.find({}, {'plex_id': 1, 'on_server': 1})}
        except Exception as e:
            logger.error(f"Error leyendo estado anterior de Mongo: {e}")
        
        # 1. Obtener Watchlist de Plex (Esto es vital, si falla aquí paramos)
        try:
            watchlist_raw = plex.get_watchlist()
            if not watchlist_raw:
                logger.warning("La Watchlist de Plex está vacía o no se pudo recuperar.")
                return
        except Exception as e:
            logger.error(f"Error crítico recuperando Watchlist: {e}")
            return

        watchlist_final = []
        
        # 2. Obtener librerías del servidor (Si falla, continuamos con on_server=False)
        server_items = []
        try:
            libraries = plex.get_server_libraries(SERVER_NAME)
            if libraries:
                for lib in libraries:
                    try:
                        lib_items = plex.get_library_items(lib)
                        for item in lib_items:
                            server_items.append({
                                "title": item.get("title", "").lower(),
                                "orig": item.get("originalTitle", "").lower(),
                                "lib": lib["title"],
                                "added_at": int(item.get("addedAt", 0))
                            })
                    except Exception as e:
                        logger.warning(f"No se pudo leer la librería {lib.get('title')}: {e}")
            else:
                logger.warning(f"No se encontró el servidor '{SERVER_NAME}' o no es accesible.")
        except Exception as e:
            logger.error(f"Error conectando con el servidor Plex para el cruce: {e}")

        # 3. Procesar y Cruzar (Independiente de si el servidor falló)
        for item in watchlist_raw:
            plex_id = item.get("ratingKey")
            title = item.get("title")
            orig = item.get("originalTitle")
            year = item.get("year")
            type_ = "Película" if item.get("type") == "movie" else "Serie"
            thumb = item.get("thumb")
            
            # Gestión de imagen
            image_url = thumb if thumb and thumb.startswith('http') else None
            if not image_url and thumb:
                image_url = f"https://metadata.provider.plex.tv{thumb}?X-Plex-Token={PLEX_TOKEN}"
            
            keys = {title.lower()} if title else set()
            if orig: keys.add(orig.lower())
            
            # Verificar disponibilidad
            on_server = False
            found_in_libs = []
            added_at = 0
            for s_item in server_items:
                if (s_item["title"] and s_item["title"] in keys) or (s_item["orig"] and s_item["orig"] in keys):
                    on_server = True
                    added_at = s_item["added_at"]
                    if s_item["lib"] not in found_in_libs:
                        found_in_libs.append(s_item["lib"])
            
            # 4. Obtener nota de TMDB (Siempre se intenta, haya servidor o no)
            tmdb_score = "N/A"
            if TMDB_API_KEY:
                try:
                    import requests
                    search_type = "movie" if item.get("type") == "movie" else "tv"
                    query = orig if orig else title
                    if query:
                        tmdb_url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={TMDB_API_KEY}&query={urllib.parse.quote(query)}&year={year}"
                        tmdb_res = requests.get(tmdb_url, timeout=5).json()
                        
                        if not tmdb_res.get("results") and title:
                            tmdb_url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={TMDB_API_KEY}&query={urllib.parse.quote(title)}&year={year}"
                            tmdb_res = requests.get(tmdb_url, timeout=5).json()

                        if tmdb_res.get("results"):
                            tmdb_score = str(round(tmdb_res["results"][0].get("vote_average", 0), 1))
                except Exception as e:
                    logger.error(f"Error TMDB para {title}: {e}")

            new_item = {
                "plex_id": plex_id,
                "title": title,
                "orig": orig,
                "year": year,
                "type": type_,
                "image": image_url,
                "url": f"https://www.filmaffinity.com/es/search.php?stext={urllib.parse.quote(title or '')}",
                "on_server": on_server,
                "libraries": found_in_libs,
                "score": tmdb_score,
                "added_at": added_at
            }
            watchlist_final.append(new_item)

            # 5. Detectar Novedad para Telegram
            was_on_server = old_data.get(plex_id, False)
            if on_server and not was_on_server:
                send_telegram_notification(new_item)

        # 6. Guardar en MongoDB
        if watchlist_final:
            collection.delete_many({})
            collection.insert_many(watchlist_final)
            logger.info(f"Sincronización finalizada. Guardados {len(watchlist_final)} elementos.")
        
    except Exception as e:
        logger.error(f"Error general en el proceso de sincronización: {e}")
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
    app.run(host='0.0.0.0', port=PORT)
