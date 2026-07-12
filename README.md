# Plex Watchlist Manager (Cloud Edition) ✨

Sistema de gestión y visualización de tu Plex Watchlist con base de datos en la nube y sincronización automática.

## 🚀 Características
- **Base de Datos Cloud**: Usa MongoDB Atlas para un acceso rápido y persistente.
- **Sincronización Automática**: El servidor refresca los datos de Plex cada hora de forma autónoma.
- **Interfaz Web Premium**: Panel visual con pósters, badges de disponibilidad y links a FilmAffinity.
- **Despliegue Gratuito**: Preparado para funcionar en Render/Railway.

## 🛠️ Configuración Cloud

### 1. Base de Datos (MongoDB Atlas)
1. Crea un clúster gratuito en [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Crea un usuario y obtén tu cadena de conexión (Connection String).
3. Añade la URI a tus variables de entorno como `MONGO_URI`.

### 2. Variables de Entorno
Necesitas configurar las siguientes variables en tu host cloud (Render/Railway):
- `PLEX_TOKEN`: Tu token de Plex Discover.
- `SERVER_NAME`: El nombre de tu servidor Plex (ej. "Navidad").
- `MONGO_URI`: Tu conexión a MongoDB Atlas.
- `PORT`: 5000 (por defecto).

### 3. Despliegue en Render
1. Conecta este repositorio a [Render](https://render.com/).
2. Crea un "Web Service".
3. Usa la configuración:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Añade las variables de entorno en la sección "Environment".

## 🖥️ Uso Local
1. Crea y activa un entorno virtual:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Instala dependencias: `pip install -r requirements.txt`
3. Copia `.env.example` a `.env` y rellena tus credenciales.
4. Ejecuta: `python app.py`
5. Abre `http://localhost:5000`

### Variables opcionales
- `SYNC_INTERVAL_HOURS`: cada cuántas horas sincroniza (por defecto `24`).
- `FULL_SYNC_INTERVAL_DAYS`: cada cuántos días se hace una reconciliación completa
  (por defecto `7`). Entre medias, las syncs son incrementales.
- `RUN_SCHEDULER`: `1` (por defecto) activa el scheduler interno. Ponlo a `0` si
  despliegas con varios workers de gunicorn (evita sincronizaciones duplicadas) y
  mueves la sync a un cron externo.

### Modos de sincronización
- **Incremental** (por defecto): solo pide al servidor las altas desde el último
  sync exitoso. Rápido y con poca huella en el servidor.
- **Completa**: escanea todas las librerías y recalcula la disponibilidad. Se
  ejecuta automáticamente cada `FULL_SYNC_INTERVAL_DAYS`, en el primer sync, o
  bajo demanda con `GET /api/sync?full=1`. Corrige los puntos ciegos del
  incremental (bajas del servidor y elementos ya presentes de antes).

## 🗂️ Estructura
- `app.py` — app Flask (rutas + arranque del scheduler), deliberadamente fino.
- `config.py` — configuración desde variables de entorno.
- `db.py` — conexión a MongoDB y colecciones.
- `sync.py` — orquestación de la sincronización Plex → Mongo.
- `matching.py` — cruce watchlist ↔ servidor (función pura, testeable).
- `tmdb.py` — nota media de TMDB.
- `notifications.py` — avisos por Telegram.
- `plex_api.py` — cliente HTTP de la API de Plex.

---
*Hecho con ❤️ para organizar tu cine.*
