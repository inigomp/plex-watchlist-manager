"""Acceso a MongoDB. Punto único de conexión y de las colecciones."""
from pymongo import MongoClient

import config

# MongoClient conecta de forma perezosa (no hace I/O hasta la primera operación),
# por lo que instanciarlo en el import es seguro aunque el servidor esté caído.
_client = MongoClient(config.MONGO_URI)
_db = _client["plex_manager"]

watchlist = _db["watchlist"]
sync_status = _db["sync_status"]
