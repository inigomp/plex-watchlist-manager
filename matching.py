"""Cruce entre la watchlist de Plex y los items del servidor.

Función pura y sin dependencias: es el corazón de la lógica y el mejor punto
para añadir tests en el futuro.
"""


def find_availability(plex_id, item_guid, title, orig, year, server_items):
    """Determina si un elemento de la watchlist está en el servidor.

    Prioridad de match:
      1. GUID exacto (el más preciso).
      2. Fallback por Título + Año (con tolerancia de ±1 año), solo si ambos
         años son válidos (> 0).

    Devuelve (on_server, libraries, added_at).
    """
    on_server = False
    libraries = []
    added_at = 0

    title_l = title.lower() if title else None
    orig_l = orig.lower() if orig else None

    for s in server_items:
        guid_match = (
            (plex_id and s["guid"] and s["guid"].endswith(plex_id))
            or (item_guid and s["guid"] == item_guid)
        )

        title_match = False
        year_match = False
        if not guid_match and year and year > 0 and s["year"] > 0:
            title_match = (
                (title_l and s["title"] == title_l)
                or (orig_l and s["orig"] == orig_l)
                or (title_l and s["orig"] == title_l)
                or (orig_l and s["title"] == orig_l)
            )
            year_match = abs(s["year"] - year) <= 1

        if guid_match or (title_match and year_match):
            on_server = True
            added_at = s["added_at"]
            if s["lib"] not in libraries:
                libraries.append(s["lib"])
            if guid_match:
                break  # Match definitivo, no seguimos buscando.

    return on_server, libraries, added_at
