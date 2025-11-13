# main_menu.py
# Menú principal para gestionar pool de artistas, generar recomendaciones y crear playlist.

from typing import List, Dict, Optional
from datetime import datetime
import json
import requests  # lo usamos para listar playlists/editar
from create_playlist import add_tracks_to_playlist  # ya lo tienes, se reutiliza

from auth_tokens import SpotifyAuth
from search_artists import search_artists, format_artist_row
from pool_store import load_pool, save_pool, remove_by_index
from generate_recs import (
    MARKET,                      # usa SP_MARKET si está seteada en tu entorno
    parse_release_filter,        # "6m", "2a", "2010" -> filtros
    recommendations_from_artists # motor de recomendaciones (con fallback si /recommendations falla)
)
from create_playlist import (
    get_current_user_id,
    create_playlist,
    add_tracks_to_playlist,
)

# ---------- utilidades locales ----------

def normalize_artist(a: dict) -> Dict:
    return {
        "id": a.get("id"),
        "name": a.get("name"),
        "genres": a.get("genres", []),
        "followers": a.get("followers", {}).get("total", 0),
        "popularity": a.get("popularity", 0),
        "url": f"https://open.spotify.com/artist/{a.get('id')}",
    }

def add_to_pool(pool: List[Dict], artist: Dict) -> bool:
    if not artist.get("id"):
        return False
    if any(a["id"] == artist["id"] for a in pool):
        return False
    pool.append(artist)
    return True

def print_pool(pool: List[Dict]) -> None:
    if not pool:
        print("\n(Pool vacío)")
        return
    print("\nPool actual:")
    for i, a in enumerate(pool, 1):
        g = ", ".join(a.get("genres", [])[:3]) or "—"
        print(f"{i:2d}. {a['name']}  |  {a.get('followers',0):,} seguidores  |  pop {a.get('popularity',0)}  |  {g}  |  {a.get('url')}")

def load_track_ids_from_memory(tracks: List[Dict]) -> List[str]:
    # Dedup preservando orden
    seen, out = set(), []
    for t in tracks:
        tid = t.get("id")
        if tid and tid not in seen:
            seen.add(tid); out.append(tid)
    return out

# === Helpers para listar y editar playlists existentes ===
SPOTIFY_API = "https://api.spotify.com/v1"

def list_user_playlists(auth: SpotifyAuth, limit: int = 50):
    """
    Lista todas las playlists visibles del usuario (requiere token de USUARIO).
    Para ver privadas: scope playlist-read-private.
    """
    headers = auth.bearer_headers_user()
    url = f"{SPOTIFY_API}/me/playlists"
    params = {"limit": min(limit, 50), "offset": 0}
    items = []

    while True:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        if r.status_code == 401:
            headers = auth.bearer_headers_user()
            r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        items.extend(data.get("items", []) or [])
        next_url = data.get("next")
        if not next_url:
            break
        url = next_url
        params = None
    return items

def format_playlist_row(p: dict, idx: int) -> str:
    name = p.get("name", "—")
    pid = p.get("id", "—")
    owner = (p.get("owner") or {}).get("display_name") or (p.get("owner") or {}).get("id") or "—"
    total = (p.get("tracks") or {}).get("total", 0)
    public = "sí" if p.get("public") else "no"
    url = (p.get("external_urls") or {}).get("spotify", f"https://open.spotify.com/playlist/{pid}")
    return f"{idx:2d}. {name}  |  owner: {owner}  |  tracks: {total}  |  pública: {public}  |  {url}"

def replace_playlist_with_tracks(auth: SpotifyAuth, playlist_id: str, track_ids: list):
    """
    Reemplaza TODO el contenido de la playlist con track_ids (orden conservado).
    - PUT con los primeros 100
    - POST en bloques de 100 para el resto
    Requiere token de USUARIO con playlist-modify-public (y/o private).
    """
    if not track_ids:
        raise ValueError("La lista de tracks está vacía.")
    headers = auth.bearer_headers_user()
    uris = [f"spotify:track:{tid}" for tid in track_ids if tid]

    # PUT reemplaza contenido con hasta 100 URIs
    first_chunk = uris[:100]
    r = requests.put(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks",
                     headers=headers, json={"uris": first_chunk}, timeout=25)
    if r.status_code in (401, 403):
        try: msg = r.json()
        except Exception: msg = r.text
        raise RuntimeError(f"Error reemplazando playlist (status {r.status_code}): {msg}")
    r.raise_for_status()

    # POST agrega el resto
    i = 100
    while i < len(uris):
        chunk = uris[i:i+100]
        r = requests.post(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks",
                          headers=headers, json={"uris": chunk}, timeout=25)
        if r.status_code in (401, 403):
            try: msg = r.json()
            except Exception: msg = r.text
            raise RuntimeError(f"Error agregando tracks (status {r.status_code}): {msg}")
        r.raise_for_status()
        i += 100


# ---------- flujo principal ----------

def main():
    print("== Spotify Playlist Builder ==")
    auth = SpotifyAuth()  # usa .env para tokens
    headers = auth.bearer_headers()  # no lo usamos mucho aquí, pero valida auth

    # pool persistente
    pool: List[Dict] = load_pool()
    print(f"Pool cargado: {len(pool)} artistas. MARKET={MARKET}")

    generated_tracks: List[Dict] = []  # cache en memoria de la última generación

    while True:
        print("\n=== Menú Principal ===")
        print("1) Buscar y agregar artista al pool")
        print("2) Ver pool")
        print("3) Eliminar artista del pool")
        print("4) Guardar pool en artists.json")
        print("5) Generar recomendaciones (playlist_recs.json)")
        print("6) Crear playlist y (opcional) agregar canciones de la última generación")
        print("7) Editar playlist existente (reemplazar por recomendaciones)")
        print("0) Salir")

        choice = input("> ").strip()

        if choice == "1":
            q = input("\nNombre del artista/banda:\n> ").strip()
            if not q:
                continue
            try:
                items = search_artists(q, headers=headers, limit=10, market=MARKET)
            except Exception as e:
                print("Error al buscar:", e)
                continue

            if not items:
                print("No se encontraron artistas.")
                continue

            print("\nResultados:")
            for i, a in enumerate(items, 1):
                print(format_artist_row(a, i))

            print("\nElige un número (o Enter para cancelar):")
            sel = input("> ").strip()
            if not sel:
                continue
            if sel.isdigit():
                idx = int(sel)
                if 1 <= idx <= len(items):
                    picked = items[idx - 1]
                    norm = normalize_artist(picked)
                    if add_to_pool(pool, norm):
                        print(f"Añadido: {norm['name']}")
                        save_pool(pool)
                    else:
                        print("Ese artista ya estaba en el pool (o faltan datos).")
                else:
                    print("Índice inválido.")

        elif choice == "2":
            print_pool(pool)

        elif choice == "3":
            print_pool(pool)
            if not pool:
                continue
            print("\nNúmero a eliminar (o Enter para cancelar):")
            sel = input("> ").strip()
            if not sel:
                continue
            if sel.isdigit():
                removed = remove_by_index(pool, int(sel))
                if removed:
                    print(f"Eliminado: {removed['name']}")
                else:
                    print("Índice inválido.")
            else:
                print("Entrada inválida.")

        elif choice == "4":
            save_pool(pool)
            print("✔ Guardado en artists.json")

        elif choice == "5":
            if not pool:
                print("No hay artistas en tu pool. Agrega primero.")
                continue

            # parámetros
            total_raw = input("¿Cuántas canciones quieres? (100–200) [150]:\n> ").strip()
            total_tracks = 150 if not total_raw.isdigit() else max(1, min(int(total_raw), 200))
            pop_raw = input("Popularidad mínima (0–100, Enter para omitir):\n> ").strip()
            min_popularity = int(pop_raw) if pop_raw.isdigit() else None
            rf = input(
                "Filtro de fecha (opcional):\n"
                "- '6m' últimos 6 meses, '2a' últimos 2 años, o un año como '2010' (clásicos antes de 2010).\n"
                "- Enter para no filtrar.\n> "
            ).strip()
            within_days, before_year = parse_release_filter(rf)

            artist_ids = [a["id"] for a in pool if a.get("id")]

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
            print(f"Obtenidas {len(tracks)} pistas únicas.")

            # guardar playlist_recs.json
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

            # muestra
            for t in tracks[:min(10, len(tracks))]:
                print(f"- {t['name']} — {', '.join(t['artists'])} ({t.get('release_date','—')})")

            # guarda en memoria para la opción 6
            generated_tracks = tracks

        elif choice == "6":
            # Crear playlist y agregar tracks (de la última generación en memoria)
            try:
                user_id = get_current_user_id(auth)  # usa token de usuario
            except Exception as e:
                print("No se pudo obtener el usuario. Verifica scopes/refresh token:", e)
                continue

            name = input("Nombre de la playlist:\n> ").strip() or "AutoMix"
            desc = input("Descripción (opcional):\n> ").strip() or ""
            # Por ahora solo públicas (si vas a usar privadas, asegúrate de tener el scope playlist-modify-private)
            pub_in = input("¿Playlist pública? (s/n) [s]:\n> ").strip().lower()
            public = (pub_in in ("", "s"))

            try:
                playlist_id = create_playlist(auth, user_id, name=name, description=desc, public=public)
            except Exception as e:
                print("Error al crear la playlist:", e)
                continue

            print(f"✔ Playlist creada: {name} (id={playlist_id})")

            # ¿De dónde tomamos los tracks?
            if generated_tracks:
                use_mem = input("¿Agregar canciones de la última generación? (s/n) [s]:\n> ").strip().lower()
                if use_mem in ("", "s"):
                    ids = load_track_ids_from_memory(generated_tracks)
                else:
                    ids = []
            else:
                # Intentar cargar desde playlist_recs.json
                load_file = input("No hay generación en memoria. ¿Cargar playlist_recs.json? (s/n) [s]:\n> ").strip().lower()
                ids = []
                if load_file in ("", "s"):
                    try:
                        with open("playlist_recs.json", "r", encoding="utf-8") as f:
                            data = json.load(f)
                            ids = [t.get("id") for t in data.get("tracks", []) if t.get("id")]
                            # dedup
                            seen, uniq = set(), []
                            for tid in ids:
                                if tid not in seen:
                                    seen.add(tid); uniq.append(tid)
                            ids = uniq
                    except FileNotFoundError:
                        print("No existe playlist_recs.json.")

            if ids:
                try:
                    add_tracks_to_playlist(auth, playlist_id, ids)
                    print(f"✔ Agregadas {len(ids)} canciones a la playlist.")
                except Exception as e:
                    print("Error al agregar canciones:", e)
            else:
                print("No se agregaron canciones (lista vacía).")
        
        elif choice == "7":
            # EDITAR PLAYLIST EXISTENTE (reemplazar contenido)
            try:
                user_id = get_current_user_id(auth)  # valida token de USUARIO
            except Exception as e:
                print("No se pudo autenticar al usuario. Revisa scopes/refresh token:", e)
                continue

            print("\nObteniendo tus playlists…")
            pls = list_user_playlists(auth)
            if not pls:
                print("No se encontraron playlists (¿faltan scopes o no tienes playlists?).")
                continue

            print(f"\nSe encontraron {len(pls)} playlists:\n")
            for i, p in enumerate(pls, 1):
                print(format_playlist_row(p, i))

            print("\nElige un número para editar (o Enter para cancelar):")
            sel = input("> ").strip()
            if not sel:
                continue
            if not sel.isdigit():
                print("Entrada inválida.")
                continue
            idx = int(sel)
            if not (1 <= idx <= len(pls)):
                print("Índice fuera de rango.")
                continue

            chosen = pls[idx - 1]
            pid = chosen.get("id")
            pname = chosen.get("name", "—")
            print(f"\nEditarás: {pname} (id={pid})")

            # Fuente de tracks: memoria o JSON
            source = None
            if generated_tracks:
                source = input("¿Usar la ÚLTIMA generación en memoria? (s/n) [s]:\n> ").strip().lower()
                use_mem = (source in ("", "s"))
            else:
                use_mem = False

            tracks = []
            if use_mem:
                tracks = generated_tracks[:]  # copia
            else:
                # cargar desde playlist_recs.json
                try:
                    with open("playlist_recs.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        tracks = data.get("tracks", [])
                except FileNotFoundError:
                    print("No existe playlist_recs.json. Genera recomendaciones (opción 5) primero.")
                    continue

            if not tracks:
                print("No hay tracks disponibles para reemplazar.")
                continue

            # Ordenar por popularidad (desc) y deduplicar preservando orden
            tracks.sort(key=lambda t: (t.get("popularity") or 0), reverse=True)
            seen, track_ids = set(), []
            for t in tracks:
                tid = t.get("id")
                if tid and tid not in seen:
                    seen.add(tid); track_ids.append(tid)

            # Confirmación
            print(f"\nReemplazaremos '{pname}' con {len(track_ids)} canciones (ordenadas por popularidad). ¿Confirmas? (s/n) [s]:")
            ok = input("> ").strip().lower()
            if ok not in ("", "s"):
                print("Cancelado.")
                continue

            try:
                replace_playlist_with_tracks(auth, pid, track_ids)
                print(f"✔ Playlist '{pname}' reemplazada con {len(track_ids)} canciones.")
            except Exception as e:
                print("Error al reemplazar:", e)
        
        elif choice == "0":
            print("¡Hasta luego!")
            break

        else:
            print("Opción no válida.")

if __name__ == "__main__":
    main()