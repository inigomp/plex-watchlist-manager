"""Sincronización de la Watchlist de Plex con MongoDB.

Dos modos:
  - Incremental (por defecto): solo pide al servidor las altas desde el último
    sync exitoso y las fusiona con el estado guardado. Barato y silencioso.
  - Completo: escanea todas las librerías del servidor y recalcula la
    disponibilidad de cero. Se ejecuta automáticamente cada FULL_SYNC_INTERVAL_DAYS
    (o bajo demanda) para corregir los puntos ciegos del incremental (bajas del
    servidor y elementos que ya estaban antes del último sync).

Resistente a fallos parciales: si el servidor no responde, la watchlist se guarda
igualmente preservando el estado anterior; solo la watchlist en sí es crítica.
"""
import logging
import time
import urllib.parse

import config
from plex_api import PlexAPI
from db import watchlist as watchlist_col, sync_status as status_col
from notifications import send_telegram_notification
from tmdb import get_score
from matching import find_availability

logger = logging.getLogger(__name__)


def sync_watchlist(full=False):
    """Punto de entrada de la sincronización (scheduler y /api/sync).

    ``full=True`` fuerza una reconciliación completa. En modo automático, se
    escala a completa si nunca hubo un sync exitoso o si la última reconciliación
    completa es más antigua que FULL_SYNC_INTERVAL_DAYS.
    """
    status = _read_status()
    do_full = _should_run_full(status, full)
    since_ts = None if do_full else status.get("last_success_timestamp")

    logger.info(f"Iniciando sincronización ({'completa' if do_full else 'incremental'})...")
    try:
        plex = PlexAPI(config.PLEX_TOKEN)
        old_docs = _load_previous_docs()

        # La watchlist es el dato vital: si falla aquí, abortamos sin tocar Mongo.
        try:
            watchlist_raw = plex.get_watchlist()
        except Exception as e:
            logger.error(f"Error crítico recuperando Watchlist: {e}")
            _save_status("error", error=str(e))
            return

        if not watchlist_raw:
            logger.warning("La Watchlist de Plex está vacía o no se pudo recuperar.")
            _save_status("error", error="Watchlist vacía o irrecuperable")
            return

        # En incremental solo pedimos las altas nuevas del servidor.
        server_items = _collect_server_items(plex, since_ts=since_ts)

        incremental = not do_full
        # Solo notificamos en incremental (el delta diario). Una reconciliación
        # completa reconstruye el estado desde cero y no debe generar avisos: sería
        # un "re-baseline" que inundaría Telegram. Requiere además línea base previa.
        notify = incremental and bool(old_docs)

        watchlist_final = []
        for order, item in enumerate(watchlist_raw):
            new_item = _build_item(item, order, server_items, old_docs, incremental)
            watchlist_final.append(new_item)

            was_on_server = old_docs.get(new_item["plex_id"], {}).get("on_server", False)
            if notify and new_item["on_server"] and not was_on_server:
                send_telegram_notification(new_item)

        if watchlist_final:
            _replace_all(watchlist_final)
            _save_status("success", full=do_full)
            logger.info(
                f"Sincronización {'completa' if do_full else 'incremental'} finalizada. "
                f"Guardados {len(watchlist_final)} elementos."
            )

    except Exception as e:
        logger.error(f"Error general en el proceso de sincronización: {e}")
        _save_status("error", error=str(e))


def _should_run_full(status, forced):
    """Decide si esta ejecución debe ser una reconciliación completa."""
    if forced:
        return True
    if status.get("last_success_timestamp") is None:
        return True  # Primer sync: necesitamos una línea base completa.
    last_full = status.get("last_full_timestamp")
    if last_full is None:
        return True
    return (int(time.time()) - last_full) >= config.FULL_SYNC_INTERVAL_DAYS * 86400


def _read_status():
    return status_col.find_one({"id": "last_sync"}) or {}


def _load_previous_docs():
    """Carga el estado anterior de Mongo indexado por plex_id.

    Se reutiliza para preservar disponibilidad, nota (score) y dueños (owners)
    en las sincronizaciones incrementales.
    """
    docs = {}
    try:
        for doc in watchlist_col.find({}, {"_id": 0}):
            pid = doc.get("plex_id")
            if pid:
                docs[pid] = doc
    except Exception as e:
        logger.error(f"Error leyendo estado anterior de Mongo: {e}")
    return docs


def _collect_server_items(plex, since_ts=None):
    """Aplana las librerías del servidor en una lista de items normalizados.

    Si ``since_ts`` es None escanea todo (modo completo); si tiene valor, pide
    solo las altas desde esa fecha (modo incremental). Ante un fallo del servidor
    devuelve lista vacía y la sync continúa preservando el estado anterior.
    """
    server_items = []
    try:
        libraries = plex.get_server_libraries(config.SERVER_NAME)
        if not libraries:
            logger.warning(
                f"No se encontró el servidor '{config.SERVER_NAME}' o no es accesible."
            )
            return server_items

        for lib in libraries:
            try:
                if since_ts is None:
                    lib_items = plex.get_library_items(lib)
                else:
                    lib_items = plex.get_library_items_since(lib, since_ts)
                for item in lib_items:
                    server_items.append(_normalize_server_item(item, lib))
            except Exception as e:
                logger.warning(f"No se pudo leer la librería {lib.get('title')}: {e}")
    except Exception as e:
        logger.error(f"Error conectando con el servidor Plex para el cruce: {e}")

    return server_items


def _normalize_server_item(item, lib):
    return {
        "title": item.get("title", "").lower(),
        "orig": item.get("originalTitle", "").lower(),
        "year": int(item.get("year", 0) or 0),
        "guid": item.get("guid"),
        "lib": lib["title"],
        "added_at": int(item.get("addedAt", 0) or 0),
    }


def _build_item(item, order, server_items, old_docs, incremental):
    """Construye el documento final de un elemento de la watchlist.

    En modo incremental parte del estado anterior y solo lo MEJORA: si una de las
    altas nuevas del servidor coincide, marca on_server=True; nunca lo degrada a
    False (eso es trabajo de la reconciliación completa). Además reutiliza la nota
    y solo consulta TMDB para elementos nuevos en la watchlist.
    """
    plex_id = item.get("ratingKey")
    title = item.get("title")
    orig = item.get("originalTitle")
    year = item.get("year")
    item_type = item.get("type")
    type_label = "Película" if item_type == "movie" else "Serie"

    old = old_docs.get(plex_id, {})

    match_on_server, match_libs, match_added = find_availability(
        plex_id, item.get("guid"), title, orig, year, server_items
    )

    if incremental:
        on_server = old.get("on_server", False) or match_on_server
        libraries = _merge_libs(old.get("libraries", []), match_libs)
        added_at = match_added or old.get("added_at", 0)
        # La nota se reutiliza; solo se consulta TMDB para altas nuevas de watchlist.
        if plex_id in old_docs:
            score = old.get("score", "N/A")
        else:
            score = get_score(item_type, title, orig, year)
    else:
        on_server = match_on_server
        libraries = match_libs
        added_at = match_added
        score = get_score(item_type, title, orig, year)

    return {
        "plex_id": plex_id,
        "title": title,
        "orig": orig,
        "year": year,
        "type": type_label,
        "image": _build_image_url(item.get("thumb")),
        "url": f"https://www.filmaffinity.com/es/search.php?stext={urllib.parse.quote(title or '')}",
        "on_server": on_server,
        "libraries": libraries,
        "score": score,
        "added_at": added_at,
        "owners": old.get("owners", []),
        "watchlist_order": order,
    }


def _merge_libs(old_libs, new_libs):
    """Une las librerías previas con las nuevas coincidencias, sin duplicar."""
    merged = list(old_libs)
    for lib in new_libs:
        if lib not in merged:
            merged.append(lib)
    return merged


def _build_image_url(thumb):
    """Construye la URL del póster.

    OJO: cuando la imagen viene del provider de Plex, la URL incluye el
    PLEX_TOKEN y queda expuesto en el frontend. Aceptable para uso personal;
    a futuro conviene proxear la imagen a través del backend.
    """
    if thumb and thumb.startswith("http"):
        return thumb
    if thumb:
        return f"https://metadata.provider.plex.tv{thumb}?X-Plex-Token={config.PLEX_TOKEN}"
    return None


def _replace_all(items):
    """Reemplaza toda la colección de watchlist.

    Nota: no es atómico. Hay una ventana breve en la que la colección queda
    vacía entre el delete y el insert.
    """
    watchlist_col.delete_many({})
    watchlist_col.insert_many(items)


def _save_status(status, full=False, error=None):
    """Registra el resultado de la última sincronización para /api/status.

    Guarda además marcas de tiempo separadas para el último éxito y la última
    reconciliación completa, que gobiernan el modo incremental/completo.
    """
    now = int(time.time())
    doc = {
        "status": status,
        "timestamp": now,
        "server": config.SERVER_NAME,
        "mode": "full" if full else "incremental",
    }
    if error is not None:
        doc["error"] = error
    if status == "success":
        doc["last_success_timestamp"] = now
        if full:
            doc["last_full_timestamp"] = now
    status_col.update_one({"id": "last_sync"}, {"$set": doc}, upsert=True)
