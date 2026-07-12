# Plex Watchlist Manager (Cloud Edition) ✨

Sistema de gestión y visualización de tu Plex Watchlist con base de datos en la nube y sincronización automática.

## 🚀 Características
- **Base de Datos Cloud**: Usa MongoDB Atlas para un acceso rápido y persistente.
- **Sincronización Automática**: Un cron externo (o el scheduler interno) refresca los datos de Plex de forma periódica.
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

### 3. Despliegue en Render (plan free)
1. Conecta este repositorio a [Render](https://render.com/).
2. Crea un "Web Service".
3. Usa la configuración:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Añade las variables de entorno en la sección "Environment". En free, deja
   `RUN_SCHEDULER=0` (ver abajo el porqué).

### 4. Sincronización en Render free (cron externo)
El plan free de Render **duerme el servicio tras ~15 min sin tráfico**, lo que mata
el scheduler interno. Por eso la sync se dispara desde fuera:

1. Deja `RUN_SCHEDULER=0` (el hilo interno no sirve en free).
2. Crea un cron gratuito (p. ej. [cron-job.org](https://cron-job.org)) que haga
   `GET https://TU-APP.onrender.com/api/sync` una o dos veces al día.
3. Cada llamada despierta el servicio **y** lanza la sync. Corre en modo auto:
   incremental casi siempre, escalando a reconciliación completa cada
   `FULL_SYNC_INTERVAL_DAYS` de forma automática. No hace falta un cron aparte
   para la completa.

> En un host persistente (VPS, Render de pago, local) no necesitas cron: pon
> `RUN_SCHEDULER=1` y el scheduler interno se encarga.

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
- `RUN_SCHEDULER`: `0` (por defecto) desactiva el scheduler interno; la sync la
  dispara un cron externo contra `/api/sync` (necesario en Render free, donde el
  proceso se duerme). Ponlo a `1` solo en un host persistente.

### Modos de sincronización
- **Incremental** (por defecto): solo pide al servidor las altas desde el último
  sync exitoso. Rápido y con poca huella en el servidor.
- **Completa**: escanea todas las librerías y recalcula la disponibilidad. Se
  ejecuta automáticamente cada `FULL_SYNC_INTERVAL_DAYS`, en el primer sync, o
  bajo demanda con `GET /api/sync?full=1`. Corrige los puntos ciegos del
  incremental (bajas del servidor y elementos ya presentes de antes).

## 🧪 Tests
```powershell
pip install -r requirements-dev.txt
pytest
```
Cubren la lógica pura: el cruce watchlist ↔ servidor (`matching.py`) y la lógica
incremental de sync (modo, merge y construcción de items). No tocan red ni Mongo.

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
