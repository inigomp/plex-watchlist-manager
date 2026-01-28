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
1. Instala dependencias: `pip install -r requirements.txt`
2. Crea un archivo `.env` con tus credenciales.
3. Ejecuta: `python app.py`
4. Abre `http://localhost:5000`

---
*Hecho con ❤️ para organizar tu cine.*
