# replace_playlist.py
# Reemplaza TODO el contenido de una playlist con las recomendaciones de playlist_recs.json
# Requisitos: auth_tokens.py (token de usuario con scopes playlist-modify-*), requests

import json
from typing import List
import requests

from auth_tokens import SpotifyAuth  # usa bearer_headers_user()

SPOTIFY_API = "https://api.spotify.com/v1"

def load_track_ids_from_json(path: str = "playlist_recs.json") -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tracks = data.get("tracks", [])
    # Si quieres, asegurar aquí el orden por popularidad desc (por si el JSON no vino ordenado):
    tracks.sort(key=lambda t: (t.get("popularity") or 0), reverse=True)
    # dedup preservando orden
    seen, ids = set(), []
    for t in tracks:
        tid = t.get("id")
        if tid and tid not in seen:
            seen.add(tid)
            ids.append(tid)
    return ids

def replace_playlist_with_tracks(auth: SpotifyAuth, playlist_id: str, track_ids: List[str]) -> None:
    """
    Reemplaza todo el contenido de la playlist con track_ids.
    - PUT /playlists/{id}/tracks (máx 100 URIs) -> reemplaza todo
    - Si hay >100, POST /playlists/{id}/tracks para agregar el resto en bloques de 100
    """
    if not track_ids:
        raise ValueError("La lista de tracks está vacía. Genera recomendaciones primero.")

    headers = auth.bearer_headers_user()  # token de USUARIO
    uris = [f"spotify:track:{tid}" for tid in track_ids]

    # 1) Reemplazar con los primeros 100 (o menos)
    first_chunk = uris[:100]
    r = requests.put(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks",
                     headers=headers, json={"uris": first_chunk}, timeout=25)
    if r.status_code in (401, 403):
        try:
            msg = r.json()
        except Exception:
            msg = r.text
        raise RuntimeError(f"Error reemplazando playlist (status {r.status_code}): {msg}")
    r.raise_for_status()

    # 2) Agregar el resto en bloques de 100
    i = 100
    while i < len(uris):
        chunk = uris[i:i+100]
        r = requests.post(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks",
                          headers=headers, json={"uris": chunk}, timeout=25)
        if r.status_code in (401, 403):
            try:
                msg = r.json()
            except Exception:
                msg = r.text
            raise RuntimeError(f"Error agregando tracks (status {r.status_code}): {msg}")
        r.raise_for_status()
        i += 100

if __name__ == "__main__":
    auth = SpotifyAuth()

    # 1) Pide el ID de la playlist que quieres reemplazar (puedes obtenerlo con list_playlists.py)
    pid = input("Pega el Playlist ID a reemplazar por recomendaciones:\n> ").strip()
    if not pid:
        print("No ingresaste un playlist_id.")
        raise SystemExit(0)

    # 2) Carga recomendaciones
    try:
        ids = load_track_ids_from_json("playlist_recs.json")
    except FileNotFoundError:
        print("No se encontró playlist_recs.json. Genera recomendaciones primero (opción 5 del menú).")
        raise SystemExit(1)

    if not ids:
        print("playlist_recs.json no tiene tracks válidos.")
        raise SystemExit(1)

    # 3) Ejecuta el reemplazo
    try:
        replace_playlist_with_tracks(auth, pid, ids)
        print(f"✔ Playlist {pid} reemplazada con {len(ids)} canciones (ordenadas por popularidad).")
    except Exception as e:
        print("Error:", e)
