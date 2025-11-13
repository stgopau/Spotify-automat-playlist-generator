# auth_tokens.py
# Paso 1: cargar credenciales y obtener access token (sin usar aún la API de búsqueda)

import os
import base64
import requests
from typing import Optional, Dict
from dotenv import load_dotenv

ACCOUNTS = "https://accounts.spotify.com/api/token"

class SpotifyAuth:
    def __init__(self):
        # 1) Cargar .env
        load_dotenv()
        self.client_id = os.getenv("SPOTIPY_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "").strip()
        self.redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "").strip()
        self.refresh_token = os.getenv("SPOTIPY_REFRESH_TOKEN", "").strip()

        if not self.client_id or not self.client_secret:
            raise RuntimeError("Faltan SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET en .env")

        self.access_token: Optional[str] = None

    # --- helpers internos ---
    def _basic_auth_header(self) -> Dict[str, str]:
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        return {"Authorization": f"Basic {auth}"}

    # --- flujos de token ---
    def refresh_access_token(self) -> str:
        if not self.refresh_token:
            raise RuntimeError("No hay SPOTIPY_REFRESH_TOKEN para refrescar el access token.")
        data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}
        r = requests.post(ACCOUNTS, headers=self._basic_auth_header(), data=data, timeout=20)
        r.raise_for_status()
        self.access_token = r.json()["access_token"]
        return self.access_token

    def client_credentials_token(self) -> str:
        data = {"grant_type": "client_credentials"}
        r = requests.post(ACCOUNTS, headers=self._basic_auth_header(), data=data, timeout=20)
        r.raise_for_status()
        self.access_token = r.json()["access_token"]
        return self.access_token

    # --- API pública mínima ---
    def get_access_token(self, prefer_user: bool = True) -> str:
        """
        prefer_user=True: intenta refrescar con refresh_token; si falla, cae a client_credentials.
        """
        if self.access_token:
            return self.access_token
        if prefer_user and self.refresh_token:
            try:
                return self.refresh_access_token()
            except Exception:
                # si refrescar falla (o no hay refresh), usa client credentials
                pass
        return self.client_credentials_token()

    def bearer_headers(self) -> Dict[str, str]:
        """
        Cabecera Authorization lista para usar en futuras llamadas a la API.
        """
        return {"Authorization": f"Bearer {self.get_access_token(prefer_user=True)}"}
    
    def get_user_access_token(self) -> str:
        """
        Devuelve SIEMPRE un access token de USUARIO.
        Lanza error si no existe refresh_token.
        """
        if not self.refresh_token:
            raise RuntimeError("No hay SPOTIPY_REFRESH_TOKEN: se necesita token de USUARIO para modificar playlists.")
        # Si ya tenemos access_token en memoria, úsalo; si falla la API, refrescaremos.
        if self.access_token:
            return self.access_token
        return self.refresh_access_token()

    def bearer_headers_user(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.get_user_access_token()}"}

# Uso mínimo manual:
if __name__ == "__main__":
    auth = SpotifyAuth()
    token = auth.get_access_token(prefer_user=True)
    # Imprime una versión enmascarada (para no exponer el token completo)
    print(f"Access token (parcial): {token[:12]}... (len={len(token)})")
