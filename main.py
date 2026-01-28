import os
from plex_api import PlexAPI
from fa_scraper import FAScraper

# --- Configuración ---
PLEX_TOKEN = "T8ibaxz7N8Us9toUkHbu"
SERVER_NAME = "Navidad"
# ---------------------

def main():
    plex = PlexAPI(PLEX_TOKEN)
    fa = FAScraper()

    print(f"--- Plex Watchlist Manager ---")
    
    # 1. Obtener Watchlist
    watchlist_raw = plex.get_watchlist()
    watchlist = {} # key -> metadata
    for item in watchlist_raw:
        title = item.get("title")
        orig = item.get("originalTitle")
        keys = {title.lower()}
        if orig: keys.add(orig.lower())
        
        watchlist[tuple(keys)] = {
            "title": title,
            "year": item.get("year"),
            "type": item.get("type"),
            "on_server": False,
            "libraries": []
        }
    
    print(f"Watchlist cargada: {len(watchlist)} elementos.")

    # 2. Buscar en el Servidor
    libraries = plex.get_server_libraries(SERVER_NAME)
    if not libraries:
        print(f"No se pudo acceder al servidor '{SERVER_NAME}'.")
        return

    print(f"Escaneando {len(libraries)} librerías en '{SERVER_NAME}'...")
    for lib in libraries:
        items = plex.get_library_items(lib)
        for srv_item in items:
            srv_title = srv_item.get("title", "").lower()
            srv_orig = srv_item.get("originalTitle", "").lower()
            
            for keys_tuple, meta in watchlist.items():
                if srv_title in keys_tuple or (srv_orig and srv_orig in keys_tuple):
                    meta["on_server"] = True
                    if lib["title"] not in meta["libraries"]:
                        meta["libraries"].append(lib["title"])

    # 3. Mostrar Resultados y (opcionalmente) enriquecer con FA
    print("\n" + "="*40)
    print(f"{'ESTADO':<10} | {'TÍTULO':<30} | {'LIBRERÍAS'}")
    print("-" * 60)
    
    for meta in watchlist.values():
        status = "✅ DISP" if meta["on_server"] else "❌ FALTA"
        libs = ", ".join(meta["libraries"]) if meta["on_server"] else "-"
        print(f"{status:<10} | {meta['title'][:30]:<30} | {libs}")

    print("="*40)
    print(f"Resumen: {sum(1 for m in watchlist.values() if m['on_server'])} de {len(watchlist)} disponibles.")

if __name__ == "__main__":
    main()
