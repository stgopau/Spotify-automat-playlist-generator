# select_and_pool.py
# Paso 3: elegir un artista de los resultados y agregarlo a un pool en memoria (sin persistencia)

from typing import List, Dict, Optional
from auth_tokens import SpotifyAuth
from search_artists import search_artists, format_artist_row  # del Bloque 2

# --- Normalización de artista (quedarnos con campos clave) ---
def normalize_artist(a: dict) -> Dict:
    return {
        "id": a.get("id"),
        "name": a.get("name"),
        "genres": a.get("genres", []),
        "followers": a.get("followers", {}).get("total", 0),
        "popularity": a.get("popularity", 0),
        "url": f"https://open.spotify.com/artist/{a.get('id')}",
    }

# --- Pool en memoria ---
def add_to_pool(pool: List[Dict], artist: Dict) -> bool:
    """Agrega evitando duplicados por id. Devuelve True si lo agregó."""
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
        print(f"{i:2d}. {a['name']}  |  {a['followers']:,} seguidores  |  pop {a['popularity']}  |  {', '.join(a['genres'][:3]) or '—'}  |  {a['url']}")

# --- UI mínima para elegir un candidato ---
def choose_one(candidates: List[dict]) -> Optional[dict]:
    if not candidates:
        return None
    print("\nElige un número (o Enter para cancelar):")
    sel = input("> ").strip()
    if not sel:
        return None
    if not sel.isdigit():
        print("Entrada inválida.")
        return None
    idx = int(sel)
    if 1 <= idx <= len(candidates):
        return candidates[idx - 1]
    print("Índice fuera de rango.")
    return None

if __name__ == "__main__":
    auth = SpotifyAuth()
    headers = auth.bearer_headers()

    pool: List[Dict] = []  # nuestro “carrito” en memoria

    while True:
        print("\n=== Búsqueda y pool de artistas ===")
        print("1) Buscar artista y agregar al pool")
        print("2) Ver pool")
        print("0) Salir")
        choice = input("> ").strip()

        if choice == "1":
            q = input("\nNombre del artista/banda:\n> ").strip()
            if not q:
                continue
            items = search_artists(q, headers=headers, limit=10, market="CL")
            if not items:
                print("No se encontraron artistas.")
                continue

            print("\nResultados:")
            for i, a in enumerate(items, 1):
                print(format_artist_row(a, i))

            picked = choose_one(items)
            if picked:
                norm = normalize_artist(picked)
                added = add_to_pool(pool, norm)
                if added:
                    print(f"\nAñadido: {norm['name']}")
                else:
                    print("\nEse artista ya estaba en el pool (o faltan datos).")

        elif choice == "2":
            print_pool(pool)

        elif choice == "0":
            break

        else:
            print("Opción no válida.")
