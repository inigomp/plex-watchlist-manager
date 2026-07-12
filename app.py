"""Aplicación Flask: rutas HTTP y arranque del scheduler.

Este módulo es deliberadamente fino: la lógica de negocio vive en sync.py,
db.py, tmdb.py, notifications.py y matching.py.
"""
import logging
import threading

import urllib3
from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

import config
from db import watchlist as watchlist_col, sync_status as status_col
from sync import sync_watchlist

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="")
    CORS(app)
    _register_routes(app)
    return app


def _register_routes(app):
    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    @app.route("/api/watchlist", methods=["GET"])
    def get_watchlist():
        # Lee directamente de la base de datos (instantáneo).
        return jsonify(list(watchlist_col.find({}, {"_id": 0})))

    @app.route("/api/watchlist/update_owners", methods=["POST"])
    def update_owners():
        """Actualiza los dueños de un elemento concreto."""
        try:
            data = request.json
            plex_id = data.get("plex_id")
            owners = data.get("owners", [])

            if not plex_id:
                return jsonify({"status": "error", "message": "Falta plex_id"}), 400

            result = watchlist_col.update_one(
                {"plex_id": plex_id}, {"$set": {"owners": owners}}
            )
            if result.matched_count > 0:
                return jsonify({"status": "success"})
            return jsonify({"status": "error", "message": "No se encontró el elemento"}), 404
        except Exception as e:
            logger.error(f"Error actualizando dueños: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/status", methods=["GET"])
    def get_status():
        status = status_col.find_one({"id": "last_sync"}, {"_id": 0})
        return jsonify(status or {"status": "unknown"})

    @app.route("/api/sync", methods=["GET", "POST"])
    def force_sync():
        if not config.PLEX_TOKEN or not config.MONGO_URI:
            return jsonify({"error": "Configuración incompleta (Tokens/Mongo)"}), 500

        # ?full=1 fuerza una reconciliación completa; por defecto, incremental.
        full = request.args.get("full") in ("1", "true", "yes")

        # En segundo plano para evitar el timeout de 30s de Render.
        threading.Thread(target=_sync_worker, args=(app, full), daemon=True).start()
        return jsonify({
            "status": "sync_initiated",
            "mode": "full" if full else "auto",
            "message": "La sincronización ha comenzado en segundo plano. "
                       "Los datos aparecerán en unos momentos.",
        })


def _sync_worker(app, full=False):
    with app.app_context():
        sync_watchlist(full=full)


def start_scheduler():
    """Arranca el scheduler horario. Debe llamarse UNA sola vez.

    Con gunicorn multi-worker se arrancaría un scheduler por worker (syncs
    duplicadas). Por eso se controla con RUN_SCHEDULER y se recomienda 1 worker,
    o mover la sync a un cron externo y arrancar con RUN_SCHEDULER=0.
    """
    if not config.RUN_SCHEDULER:
        logger.info("RUN_SCHEDULER=0: scheduler desactivado.")
        return None

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=sync_watchlist, trigger="interval", hours=config.SYNC_INTERVAL_HOURS)
    scheduler.start()
    logger.info(f"Scheduler iniciado (cada {config.SYNC_INTERVAL_HOURS}h).")
    return scheduler


# Instancia usada por gunicorn (`gunicorn app:app`) y por el arranque local.
app = create_app()
start_scheduler()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT)
