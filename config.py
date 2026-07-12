"""Configuración central de la aplicación, leída desde variables de entorno."""
import os

from dotenv import load_dotenv

load_dotenv()

# Servidor
PORT = int(os.getenv("PORT", 5000))

# Plex
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
SERVER_NAME = os.getenv("SERVER_NAME", "Navidad")

# Persistencia
MONGO_URI = os.getenv("MONGO_URI")

# Integraciones opcionales
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Sincronización automática. La watchlist cambia poco: 1 vez al día es suficiente
# y evita barridos innecesarios de las librerías del servidor.
SYNC_INTERVAL_HOURS = int(os.getenv("SYNC_INTERVAL_HOURS", 24))

# Cada cuántos días se hace una reconciliación COMPLETA (escaneo total del
# servidor). Entre medias, las syncs son incrementales (solo altas nuevas).
# La reconciliación corrige los puntos ciegos del incremental: bajas del servidor
# y elementos de la watchlist que ya estaban en el servidor de antes.
FULL_SYNC_INTERVAL_DAYS = int(os.getenv("FULL_SYNC_INTERVAL_DAYS", 7))
# Scheduler interno (hilo APScheduler dentro del proceso). Desactivado por defecto:
# en Render free el proceso se duerme y el hilo muere, así que la sync se dispara
# desde un cron externo que golpea /api/sync. Ponlo a "1" solo en un host
# persistente (VPS, Render de pago, local) donde el proceso no muere.
RUN_SCHEDULER = os.getenv("RUN_SCHEDULER", "0") == "1"
