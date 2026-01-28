import requests

API_KEY = "55cdbc10bccf80f091f65712ba5cc58e"
# Probamos buscando "Despierta la furia" (Wrath of Man)
url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query=Wrath+of+Man&year=2021"

try:
    resp = requests.get(url, timeout=10)
    print(f"Status Code: {resp.status_code}")
    data = resp.json()
    if data.get("results"):
        result = data["results"][0]
        print(f"Match encontrado: {result.get('title')}")
        print(f"Nota: {result.get('vote_average')}")
    else:
        print("No se encontraron resultados en TMDB.")
        print(f"Respuesta completa: {data}")
except Exception as e:
    print(f"Error conectando con TMDB: {e}")
