# get_refresh_token.py
import os
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()  # Carga tus CLIENT_ID, CLIENT_SECRET y REDIRECT_URI desde .env

sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope=os.getenv("SPOTIPY_SCOPE"),
    cache_path=".cache"
)

# 1) Genera la URL de autorización
auth_url = sp_oauth.get_authorize_url()
print("➜ Abre esta URL en tu navegador:\n", auth_url)

# 2) Pega aquí el código que veas en la URL tras autorizar
code = input("\n➜ Copia el valor de ?code= y pega aquí: ")

# 3) Intercambia el código por tokens
token_info = sp_oauth.get_access_token(code, as_dict=True)
print("\n✅ Tu refresh token es:\n", token_info["refresh_token"])

