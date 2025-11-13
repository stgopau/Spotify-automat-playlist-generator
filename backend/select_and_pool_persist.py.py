# select_and_pool_persist.py
# Paso 4: pool persistente con cargar/guardar/eliminar

from typing import List, Dict, Optional
from auth_tokens import SpotifyAuth
from search_artists import search_artists, format_artist_row
from pool_store import load_pool, save_pool, remove_by_index

# --- Normalización y utilidades del pool ---

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

# --- CLI ---

if __name__ == "__main__":
    auth = SpotifyAuth()
    headers = auth.bearer_headers()

    # 1) Cargar pool desde disco al iniciar
    pool: List[Dict] = load_pool()
    print(f"Pool cargado: {len(pool)} artistas.")

    while True:
        print("\n=== Búsqueda y pool de artistas (persistente) ===")
        print("1) Buscar y agregar artista")
        print("2) Ver pool")
        print("3) Eliminar artista del pool")
        print("4) Guardar cambios")
        print("0) Guardar y salir")
        choice = input("> ").strip()

        if choice == "1":
            q = input("\nNombre del artista/banda:\n> ").strip()
            if not q:
                continue
            try:
                items = search_artists(q, headers=headers, limit=10, market="CL")
            except Exception as e:
                print("Error al buscar:", e)
                continue

            if not items:
                print("No se encontraron artistas.")
                continue

            print("\nResultados:")
            for i, a in enumerate(items, 1):
                print(format_artist_row(a, i))

            picked = choose_one(items)
            if picked:
                norm = normalize_artist(picked)
                if add_to_pool(pool, norm):
                    print(f"\nAñadido: {norm['name']}")
                else:
                    print("\nEse artista ya estaba en el pool (o faltan datos).")

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

        elif choice == "0":
            save_pool(pool)
            print("✔ Guardado en artists.json. ¡Hasta luego!")
            break

        else:
            print("Opción no válida.")
