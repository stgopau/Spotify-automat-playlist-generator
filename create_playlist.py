# create_playlist.py
# Paso 6: crear playlist y agregar canciones desde playlist_recs.json (opcional)

import json
from typing import List, Dict, Optional
import requests

from auth_tokens import SpotifyAuth  # Bloque 1

SPOTIFY_API = "https://api.spotify.com/v1"

# ---------- Helpers API ----------

def get_current_user_id(auth: SpotifyAuth) -> str:
    headers = auth.bearer_headers_user()  # <--- usa token de USUARIO
    r = requests.get(f"{SPOTIFY_API}/me", headers=headers, timeout=20)
    if r.status_code == 401:
        headers = auth.bearer_headers_user()
        r = requests.get(f"{SPOTIFY_API}/me", headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()["id"]

def create_playlist(auth: SpotifyAuth, user_id: str, name: str, description: str = "", public: bool = False) -> str:
    headers = auth.bearer_headers_user()  # <--- usa token de USUARIO
    payload = {"name": name, "description": description, "public": public}
    r = requests.post(f"{SPOTIFY_API}/users/{user_id}/playlists", headers=headers, json=payload, timeout=20)
    if r.status_code in (401, 403):
        try:
            msg = r.json()
        except Exception:
            msg = r.text
        raise RuntimeError(f"Error creando playlist (status {r.status_code}): {msg}")
    r.raise_for_status()
    return r.json()["id"]

def add_tracks_to_playlist(auth: SpotifyAuth, playlist_id: str, track_ids: List[str]) -> None:
    headers = auth.bearer_headers_user()  # <--- usa token de USUARIO
    uris = [f"spotify:track:{tid}" for tid in track_ids if tid]
    for i in range(0, len(uris), 100):
        chunk = uris[i:i+100]
        r = requests.post(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks", headers=headers, json={"uris": chunk}, timeout=25)
        if r.status_code in (401, 403):
            try:
                msg = r.json()
            except Exception:
                msg = r.text
            raise RuntimeError(f"Error agregando tracks (status {r.status_code}): {msg}")
        r.raise_for_status()

# ---------- Utilidades locales ----------

def load_track_ids_from_json(path: str = "playlist_recs.json") -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tracks = data.get("tracks", [])
    ids = [t.get("id") for t in tracks if t.get("id")]
    # deduplicar preservando orden
    seen, out = set(), []
    for tid in ids:
        if tid not in seen:
            seen.add(tid); out.append(tid)
    return out

# ---------- CLI mínimo ----------

if __name__ == "__main__":
    auth = SpotifyAuth()

    # 1) Obtener user_id
    user_id = get_current_user_id(auth)
    print(f"Usuario autenticado: {user_id}")

    # 2) Datos de la playlist
    print("\nCrear nueva playlist")
    name = input("Nombre de la playlist:\n> ").strip() or "AutoMix"
    desc = input("Descripción (opcional):\n> ").strip() or ""
    pub_in = input("¿Playlist pública? (s/n) [n]:\n> ").strip().lower()
    public = pub_in == "s"

    # 3) Crear
    playlist_id = create_playlist(auth, user_id, name=name, description=desc, public=public)
    print(f"✔ Playlist creada: {name} (id={playlist_id})")

    # 4) Agregar canciones (opcional)
    add_in = input("¿Agregar canciones desde playlist_recs.json? (s/n) [s]:\n> ").strip().lower()
    if add_in in ("", "s"):
        try:
            ids = load_track_ids_from_json("playlist_recs.json")
            if not ids:
                print("No se encontraron tracks en playlist_recs.json")
            else:
                add_tracks_to_playlist(auth, playlist_id, ids)
                print(f"✔ Agregadas {len(ids)} canciones a la playlist.")
        except FileNotFoundError:
            print("No existe playlist_recs.json. Genera recomendaciones primero (Bloque 5).")

    print("Listo ✅")
