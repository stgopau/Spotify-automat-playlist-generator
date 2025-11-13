# pool_store.py
# Persistencia del pool de artistas en artists.json

import os
import json
from typing import List, Dict, Optional

DEFAULT_PATH = "artists.json"

def load_pool(path: str = DEFAULT_PATH) -> List[Dict]:
    """Carga el pool desde disco; si no existe, devuelve lista vacía."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("artists", []) or []

def save_pool(pool: List[Dict], path: str = DEFAULT_PATH) -> None:
    """Guarda el pool en disco con formato legible."""
    data = {"artists": pool}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def remove_by_index(pool: List[Dict], index: int) -> Optional[Dict]:
    """Elimina por índice (1-based). Devuelve el artista eliminado o None."""
    if 1 <= index <= len(pool):
        return pool.pop(index - 1)
    return None
