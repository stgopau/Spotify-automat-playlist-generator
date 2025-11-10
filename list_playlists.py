# list_playlists.py
# Lista las playlists del usuario autenticado (propias y seguidas), con paginación.

from typing import List, Dict, Optional
import requests
from auth_tokens import SpotifyAuth  # usa bearer_headers_user()

SPOTIFY_API = "https://api.spotify.com/v1"

def list_user_playlists(auth: SpotifyAuth, limit: int = 50) -> List[Dict]:
    """
    Devuelve la lista completa de playlists visibles para el usuario.
    Requiere token de USUARIO. Para ver privadas: scope playlist-read-private.
    """
    headers = auth.bearer_headers_user()  # fuerza token de usuario
    url = f"{SPOTIFY_API}/me/playlists"
    params = {"limit": min(limit, 50), "offset": 0}
    items: List[Dict] = []

    while True:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        if r.status_code == 401:
            headers = auth.bearer_headers_user()
            r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        batch = data.get("items", []) or []
        items.extend(batch)

        next_url = data.get("next")
        if not next_url:
            break
        # Spotify ya da next con todos los params listos
        url = next_url
        params = None  # dejar que next controle

    return items

def format_playlist_row(p: Dict, idx: int) -> str:
    name = p.get("name", "—")
    pid = p.get("id", "—")
    owner = (p.get("owner") or {}).get("display_name") or (p.get("owner") or {}).get("id") or "—"
    tracks_total = (p.get("tracks") or {}).get("total", 0)
    public = "sí" if p.get("public") else "no"
    collaborative = "sí" if p.get("collaborative") else "no"
    url = (p.get("external_urls") or {}).get("spotify", f"https://open.spotify.com/playlist/{pid}")
    return f"{idx:2d}. {name}  |  owner: {owner}  |  tracks: {tracks_total}  |  pública: {public}  |  colaborativa: {collaborative}  |  {url}"

def main():
    auth = SpotifyAuth()

    print("Obteniendo tus playlists…")
    pls = list_user_playlists(auth)
    if not pls:
        print("No se encontraron playlists para este usuario (¿faltan scopes o no tienes playlists?).")
        return

    print(f"\nSe encontraron {len(pls)} playlists:\n")
    for i, p in enumerate(pls, 1):
        print(format_playlist_row(p, i))

    # (Opcional) permitir elegir una para futuras acciones
    print("\nElige un número para trabajar con esa playlist (o Enter para salir):")
    sel = input("> ").strip()
    if not sel:
        return
    if not sel.isdigit():
        print("Entrada inválida.")
        return
    idx = int(sel)
    if not (1 <= idx <= len(pls)):
        print("Índice fuera de rango.")
        return

    chosen = pls[idx - 1]
    print("\nSeleccionaste:")
    print(format_playlist_row(chosen, idx))
    print(f"\nPlaylist ID: {chosen.get('id')}")
    print("Guarda este ID; lo usaremos para editarla en el siguiente paso.")

if __name__ == "__main__":
    main()
