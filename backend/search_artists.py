# search_artists.py
# Paso 2: búsqueda simple de artistas y despliegue de candidatos

from typing import List, Dict
import requests
from auth_tokens import SpotifyAuth  # del Bloque 1

SPOTIFY_API = "https://api.spotify.com/v1"

def search_artists(q: str, headers: Dict[str, str], limit: int = 10, market: str = "CL") -> List[dict]:
    """
    Llama a /v1/search con type=artist y devuelve la lista de items.
    """
    params = {"q": q, "type": "artist", "limit": limit, "market": market}
    r = requests.get(f"{SPOTIFY_API}/search", headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("artists", {}).get("items", [])

def format_artist_row(a: dict, idx: int) -> str:
    name = a.get("name", "—")
    followers = a.get("followers", {}).get("total", 0)
    genres = ", ".join(a.get("genres", [])[:3]) or "—"
    popularity = a.get("popularity", 0)
    url = f"https://open.spotify.com/artist/{a.get('id')}"
    return f"{idx:2d}. {name}  |  {followers:,} seguidores  |  pop {popularity}  |  {genres}  |  {url}"

if __name__ == "__main__":
    auth = SpotifyAuth()
    headers = auth.bearer_headers()

    print("🔎 Búsqueda de artistas")
    q = input("Nombre del artista/banda:\n> ").strip()
    if not q:
        print("No ingresaste un término de búsqueda.")
        raise SystemExit(0)

    try:
        items = search_artists(q, headers=headers, limit=10, market="CL")
    except requests.HTTPError as e:
        print("Error HTTP al buscar:", e)
        raise SystemExit(1)

    if not items:
        print("No se encontraron artistas para esa búsqueda.")
        raise SystemExit(0)

    print("\nResultados:")
    for i, a in enumerate(items, 1):
        print(format_artist_row(a, i))
