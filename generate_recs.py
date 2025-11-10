# generate_recs.py
# Paso 5: generar recomendaciones desde artists.json con filtros simples
# Requisitos: requests, python-dotenv
# Usa: python generate_recs.py

import os
import json
import time
import random
import itertools
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

import requests

from auth_tokens import SpotifyAuth        # Bloque 1
from pool_store import load_pool           # Bloque 4

SPOTIFY_API = "https://api.spotify.com/v1"
MARKET = os.getenv("SP_MARKET", "CL")

# ----------------- Utilidades de fecha -----------------

def fetch_artist_top_tracks(auth, artist_id: str, market: str) -> List[dict]:
        headers = auth.bearer_headers()
        url = f"{SPOTIFY_API}/artists/{artist_id}/top-tracks"
        r = requests.get(url, headers=headers, params={"market": market}, timeout=20)
        if r.status_code == 401:
            headers = auth.bearer_headers()
            r = requests.get(url, headers=headers, params={"market": market}, timeout=20)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json().get("tracks", []) or []

def fetch_related_artist_ids(auth, artist_id: str) -> List[str]:
    headers = auth.bearer_headers()
    url = f"{SPOTIFY_API}/artists/{artist_id}/related-artists"
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code == 401:
        headers = auth.bearer_headers()
        r = requests.get(url, headers=headers, timeout=20)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    items = r.json().get("artists", []) or []
    return [a.get("id") for a in items if a.get("id")]

def parse_release_filter(user_input: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Devuelve (released_within_days, released_before_year)
    - '6m' => (180, None)
    - '2a' => (730, None)
    - '2010' => (None, 2010)
    - '' => (None, None)
    """
    s = (user_input or "").strip().lower()
    if not s:
        return None, None
    if s.endswith("m") and s[:-1].isdigit():
        months = int(s[:-1])
        return months * 30, None
    if s.endswith("a") and s[:-1].isdigit():
        years = int(s[:-1])
        return years * 365, None
    if len(s) == 4 and s.isdigit():
        return None, int(s)
    # Entrada no válida: ignoramos
    return None, None

def parse_release_date(date_str: str) -> datetime:
    """
    'YYYY' -> YYYY-01-01
    'YYYY-MM' -> YYYY-MM-01
    'YYYY-MM-DD' -> tal cual
    """
    parts = date_str.split("-")
    y = int(parts[0]); m = 1; d = 1
    if len(parts) >= 2:
        m = int(parts[1])
    if len(parts) == 3:
        d = int(parts[2])
    return datetime(y, m, d)

# ----------------- Llamadas API -----------------

def recommendations_from_artists(
    auth: SpotifyAuth,
    artist_ids: List[str],
    total_tracks: int = 150,
    market: str = MARKET,
    min_popularity: Optional[int] = None,
    released_within_days: Optional[int] = None,
    released_before_year: Optional[int] = None,
) -> List[Dict]:
    """
    Genera hasta total_tracks usando seeds de artistas (máx 5 por llamada), evitando duplicados.
    Aplica filtros de popularidad (API) y fecha (post-proceso).
    """
    headers = auth.bearer_headers()
    collected: List[Dict] = []
    seen = set()

    # Diversificar combinando subconjuntos de 3-5 artistas (o 1-2 si hay pocos)
    pool = artist_ids[:]
    random.shuffle(pool)
    sizes = [5, 4, 3] if len(pool) >= 3 else ([2] if len(pool) == 2 else [1])
    groups = []
    for s in sizes:
        groups += list(itertools.combinations(pool, s))
    random.shuffle(groups)

    deadline = datetime.utcnow() + timedelta(seconds=60)  # guardrail simple

    for g in groups:
        if len(collected) >= total_tracks:
            break
        if datetime.utcnow() > deadline:
            break

        params = {
            "seed_artists": ",".join(g),
            "limit": min(100, total_tracks - len(collected)),
            "market": market,
        }
        if isinstance(min_popularity, int):
             params["min_popularity"] = min_popularity

        # r = requests.get(f"{SPOTIFY_API}/recommendations", headers=headers, params=params, timeout=25)
        # if r.status_code == 401:
        #     # Token pudo expirar: refrescamos y reintentamos 1 vez
        #     headers = auth.bearer_headers()
        #     r = requests.get(f"{SPOTIFY_API}/recommendations", headers=headers, params=params, timeout=25)
        # r.raise_for_status()
        # data = r.json()
        # tracks = data.get("tracks", [])

        try:
            r = requests.get(f"{SPOTIFY_API}/recommendations", headers=headers, params=params, timeout=25)
            if r.status_code == 401:
                headers = auth.bearer_headers()
                r = requests.get(f"{SPOTIFY_API}/recommendations", headers=headers, params=params, timeout=25)
            r.raise_for_status()
            data = r.json()
            tracks = data.get("tracks", [])
        except requests.HTTPError as e:
            # Si es 404, usamos fallback.
            if r.status_code == 404:
                # Fallback: top tracks de las seeds + related artists (opcional).
                tracks = []
                seed_ids = list(g)  # el grupo de artistas de esta iteración
                # 1) top-tracks de cada seed
                for aid in seed_ids:
                    tracks += fetch_artist_top_tracks(auth, aid, market)
                # 2) related artists (descomenta si quieres aún más variedad)
                # for aid in seed_ids:
                #     for rid in fetch_related_artist_ids(auth, aid)[:3]:  # limita p.ej. a 3 relacionados por semilla
                #         tracks += fetch_artist_top_tracks(auth, rid, market)
            else:
                raise


        for t in tracks:
            tid = t.get("id")
            if not tid or tid in seen:
                continue

            # Filtro temporal (post-proceso)
            if released_within_days is not None or released_before_year is not None:
                rd = t.get("album", {}).get("release_date")
                if not rd:
                    continue
                try:
                    rel = parse_release_date(rd)
                except Exception:
                    continue

                if released_within_days is not None:
                    if datetime.utcnow() - rel > timedelta(days=released_within_days):
                        continue

                if released_before_year is not None:
                    if rel >= datetime(released_before_year, 1, 1):
                        continue

            seen.add(tid)
            collected.append({
                "id": tid,
                "name": t.get("name"),
                "artists": [a.get("name") for a in t.get("artists", [])],
                "artist_ids": [a.get("id") for a in t.get("artists", [])],
                "album": t.get("album", {}).get("name"),
                "release_date": t.get("album", {}).get("release_date"),
                "popularity": t.get("popularity"),
                "url": f"https://open.spotify.com/track/{tid}",
            })

        time.sleep(0.2)  # cortesía API

    return collected[:total_tracks]

# ----------------- CLI mínimo -----------------

def main():
    # 1) Cargar pool
    pool = load_pool()
    if not pool:
        print("No hay artistas en tu pool. Agrega artistas con el Bloque 4 y vuelve a intentar.")
        return
    print(f"Pool cargado: {len(pool)} artistas.")

    # 2) Parámetros de usuario
    try:
        total_raw = input("¿Cuántas canciones quieres? (100–200) [150 por defecto]:\n> ").strip()
        total_tracks = 150 if not total_raw.isdigit() else max(1, min(int(total_raw), 200))
    except Exception:
        total_tracks = 150

    pop_raw = input("Popularidad mínima (0–100, Enter para omitir):\n> ").strip()
    min_popularity = int(pop_raw) if pop_raw.isdigit() else None

    rf = input(
        "Filtro de fecha (opcional):\n"
        "- Usa '6m' para últimos 6 meses, '2a' para 2 años, o un año como '2010' (clásicos antes de 2010).\n"
        "- Enter para no filtrar.\n> "
    ).strip()
    within_days, before_year = parse_release_filter(rf)

    # 3) Preparar seeds
    artist_ids = [a["id"] for a in pool if a.get("id")]

    # 4) Auth
    auth = SpotifyAuth()

    # 5) Generar recomendaciones
    print("\nGenerando recomendaciones…")
    tracks = recommendations_from_artists(
        auth=auth,
        artist_ids=artist_ids,
        total_tracks=total_tracks,
        market=MARKET,
        min_popularity=min_popularity,
        released_within_days=within_days,
        released_before_year=before_year,
    )
    # Ordenar por popularidad descendente
    tracks.sort(key=lambda t: (t.get("popularity") or 0), reverse=True)


    print(f"Obtenidas {len(tracks)} pistas únicas.")

    # 6) Guardar salida
    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "market": MARKET,
        "total": len(tracks),
        "filters": {
            "min_popularity": min_popularity,
            "released_within_days": within_days,
            "released_before_year": before_year,
        },
        "artists_used": [a["name"] for a in pool],
        "tracks": tracks,
    }
    with open("playlist_recs.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("✔ Guardado en playlist_recs.json")

    # 7) Muestra rápida
    for t in tracks[:min(10, len(tracks))]:
        print(f"- {t['name']} — {', '.join(t['artists'])} ({t.get('release_date','—')})")


if __name__ == "__main__":
    main()
