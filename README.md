# Plex Watchlist Manager 🎬

Este proyecto permite gestionar y comparar tu **Plex Watchlist** universal con el contenido disponible en tu servidor **Plex** (específicamente el servidor de nombre 'Navidad').

## Características Actuales (CLI)
- **Sincronización de Watchlist**: Obtiene todos los elementos de tu lista de seguimiento (manejando paginación).
- **Match Inteligente**: Compara títulos y títulos originales para encontrar coincidencias incluso si los nombres varían entre idiomas.
- **Escaneo Multi-Librería**: Busca en todas las secciones del servidor para indicarte exactamente dónde está cada película o serie.
- **Scraper de FilmAffinity**: Capacidad modular para obtener puntuaciones y reseñas.

## Próximos Pasos (Hoja de Ruta)
- [ ] **Backend API**: Servidor en Python (FastAPI/Flask) para servir los datos en formato JSON.
- [ ] **Web Frontend**: Interfaz moderna (React/Vite) con:
    - Tabla interactiva con filtros.
    - Ordenación por **Nota en FilmAffinity**, Año y Tipo.
    - Visualización de posters y sinopsis.
    - Indicador visual de disponibilidad.

## Instalación
1. Clona el repositorio.
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta el script principal:
   ```bash
   python main.py
   ```

---
*Hecho con ❤️ para organizar tu cine.*
