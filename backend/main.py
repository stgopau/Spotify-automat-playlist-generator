# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, json
from typing import List, Dict, Optional
from fastapi import HTTPException
from datetime import datetime
from generate_recs import recommendations_from_artists, parse_release_filter
import requests

# importa tus módulos existentes
from auth_tokens import SpotifyAuth
from search_artists import search_artists as sp_search_artists

app = FastAPI()

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)  # crea la carpeta si no existe

POOL_PATH = os.path.join(DATA_DIR, "artists.json")
RECS_PATH = os.path.join(DATA_DIR, "playlist_recs.json")
SPOTIFY_API = "https://api.spotify.com/v1"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # tu app React
        "http://127.0.0.1:3000",   # por si el navegador usa esta variante
    ],
    allow_credentials=True,
    allow_methods=["*"],  # permite GET, POST, DELETE, etc.
    allow_headers=["*"],  # permite enviar headers personalizados
)

class SearchRequest(BaseModel):
    q: str
    limit: int = 10
    market: str = "CL"

class ArtistIn(BaseModel):
    id: str
    name: str
    genres: list = []
    followers: int = 0
    popularity: int = 0
    url: str = ""

class RecsRequest(BaseModel):
    total: int = 150
    min_popularity: Optional[int] = None
    date_filter: str = ""   # "6m" | "2a" | "2010" | ""
    market: str = "CL"

class CreatePlaylistRequest(BaseModel):
    name: str
    description: str = ""
    public: bool = True

class AddTracksRequest(BaseModel):
    playlist_id: str

def _load_pool() -> List[Dict]:
    if not os.path.exists(POOL_PATH):
        # si no existe, lo creamos vacío
        with open(POOL_PATH, "w", encoding="utf-8") as f:
            json.dump({"artists": []}, f, ensure_ascii=False, indent=2)
        return []
    with open(POOL_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("artists", []) or []

def _save_pool(pool: List[Dict]) -> None:
    with open(POOL_PATH, "w", encoding="utf-8") as f:
        json.dump({"artists": pool}, f, ensure_ascii=False, indent=2)

def normalize_artist(a: dict) -> Dict:
    return {
        "id": a.get("id"),
        "name": a.get("name"),
        "genres": a.get("genres", []),
        "followers": (a.get("followers") or {}).get("total", 0),
        "popularity": a.get("popularity", 0),
        "url": f"https://open.spotify.com/artist/{a.get('id')}",
    }

def _bearer_user_headers():
    # Usa SIEMPRE token de USUARIO (con scopes playlist-modify-*)
    from auth_tokens import SpotifyAuth
    return SpotifyAuth().bearer_headers_user()

def _get_current_user_id() -> str:
    headers = _bearer_user_headers()
    r = requests.get(f"{SPOTIFY_API}/me", headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()["id"]

def _create_playlist(name: str, description: str, public: bool) -> dict:
    headers = _bearer_user_headers()
    user_id = _get_current_user_id()
    payload = {"name": name, "description": description, "public": public}
    r = requests.post(f"{SPOTIFY_API}/users/{user_id}/playlists", headers=headers, json=payload, timeout=25)
    r.raise_for_status()
    return r.json()  # incluye id, external_urls, etc.

def _add_tracks_to_playlist(playlist_id: str, track_ids: list[str]) -> int:
    headers = _bearer_user_headers()
    uris = [f"spotify:track:{tid}" for tid in track_ids if tid]
    added = 0
    # Spotify acepta lotes de hasta 100
    for i in range(0, len(uris), 100):
        r = requests.post(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks",
                          headers=headers, json={"uris": uris[i:i+100]}, timeout=30)
        r.raise_for_status()
        added += len(uris[i:i+100])
    return added

# --- Helpers para leer las recomendaciones persistidas ---
def _load_recs_track_ids_sorted() -> list[str]:
    # Lee backend/data/playlist_recs.json y ordena por popularidad desc, por si acaso
    if not os.path.exists(RECS_PATH):
        return []
    with open(RECS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tracks = data.get("tracks", []) or []
    tracks.sort(key=lambda t: (t.get("popularity") or 0), reverse=True)
    seen, ids = set(), []
    for t in tracks:
        tid = t.get("id")
        if tid and tid not in seen:
            seen.add(tid); ids.append(tid)
    return ids

############################### GET ################################
@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/pool")
def api_pool_get():
    return {"artists": _load_pool()}


############################### POST ################################
@app.post("/api/search")
def api_search(body: SearchRequest):
    """
    Busca artistas en Spotify. Requiere que tu .env esté OK (SpotifyAuth).
    """
    auth = SpotifyAuth()
    headers = auth.bearer_headers()  # token (user o app), suficiente para buscar
    items = sp_search_artists(body.q, headers=headers, limit=body.limit, market=body.market)
    results = [normalize_artist(a) for a in items]
    return {"items": results}

@app.post("/api/pool/add")
def api_pool_add(artist: ArtistIn):
    pool = _load_pool()
    if any(a.get("id") == artist.id for a in pool):
        return {"artists": pool, "added": False}  # idempotente
    pool.append(artist.model_dump())
    _save_pool(pool)
    return {"artists": pool, "added": True}

@app.post("/api/recs")
def api_generate_recs(body: RecsRequest):
    # 1) cargar pool
    pool = _load_pool()
    if not pool:
        return {"total": 0, "tracks": [], "filters": {"reason": "empty_pool"}}

    artist_ids = [a.get("id") for a in pool if a.get("id")]
    within_days, before_year = parse_release_filter(body.date_filter)

    # 2) generar
    tracks = recommendations_from_artists(
        auth=SpotifyAuth(),
        artist_ids=artist_ids,
        total_tracks=max(1, min(body.total, 200)),
        market=body.market,
        min_popularity=body.min_popularity,
        released_within_days=within_days,
        released_before_year=before_year,
    )

    # 3) eliminar pistas que no cumplan min_popularity (si aplica)
    if body.min_popularity is not None:
        tracks = [t for t in tracks if (t.get("popularity") or 0) >= body.min_popularity]

    # 3)  ordenar por popularidad desc
    tracks.sort(key=lambda t: (t.get("popularity") or 0), reverse=True)

    # 4) guardar JSON en backend/data/playlist_recs.json
    out = {
        "generated_at": datetime.utcnow().isoformat()+"Z",
        "market": body.market,
        "total": len(tracks),
        "filters": {
            "min_popularity": body.min_popularity,
            "released_within_days": within_days,
            "released_before_year": before_year,
            "raw": body.date_filter,
        },
        "artists_used": [a["name"] for a in pool],
        "tracks": tracks,
    }
    with open(RECS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    return {"total": len(tracks), "tracks": tracks, "filters": out["filters"]}

@app.post("/api/playlists/create")
def api_playlists_create(body: CreatePlaylistRequest):
    """
    Crea una playlist en tu cuenta. Requiere token de USUARIO con:
    - playlist-modify-public (si public=True)
    - playlist-modify-private (si public=False)
    """
    try:
        pl = _create_playlist(body.name, body.description, body.public)
        return {
            "id": pl.get("id"),
            "name": pl.get("name"),
            "url": (pl.get("external_urls") or {}).get("spotify"),
            "public": pl.get("public"),
        }
    except requests.HTTPError as e:
        # Mensaje claro si faltan scopes: 403
        detail = e.response.json() if e.response is not None else {"error": str(e)}
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail=detail)

@app.post("/api/playlists/add")
def api_playlists_add(body: AddTracksRequest):
    """
    Agrega las últimas recomendaciones persistidas (playlist_recs.json) a la playlist indicada.
    Requiere token de USUARIO con playlist-modify-public/private según corresponda.
    """
    track_ids = _load_recs_track_ids_sorted()
    if not track_ids:
        return {"added": 0, "reason": "no_recommendations"}
    try:
        added = _add_tracks_to_playlist(body.playlist_id, track_ids)
        return {"added": added}
    except requests.HTTPError as e:
        detail = e.response.json() if e.response is not None else {"error": str(e)}
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail=detail)

################################ DELETE ################################

@app.delete("/api/pool/{artist_id}")
def api_pool_remove(artist_id: str):
    pool = _load_pool()
    new_pool = [a for a in pool if a.get("id") != artist_id]
    if len(new_pool) == len(pool):
        raise HTTPException(status_code=404, detail="Artist not in pool")
    _save_pool(new_pool)
    return {"artists": new_pool, "removed": True}

@app.delete("/api/pool")
def api_pool_clear():
    _save_pool([])
    return {"artists": [], "cleared": True}



