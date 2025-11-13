import os
import json
import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth


def load_config(config_path: str = 'config.json') -> dict:
    """
    Carga parámetros desde un JSON de configuración.

    :param config_path: Ruta al archivo JSON de configuración.
    :return: Diccionario con los valores de configuración.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def init_spotify_client() -> spotipy.Spotify:
    """
    Inicializa y retorna un cliente autenticado de Spotify usando credenciales en .env.

    Espera encontrar en .env:
      SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET,
      SPOTIPY_REDIRECT_URI, SPOTIPY_REFRESH_TOKEN

    :return: Instancia de spotipy.Spotify autenticada
    :raises ValueError: si faltan credenciales
    """
    load_dotenv()
    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')
    refresh_token = os.getenv('SPOTIPY_REFRESH_TOKEN')

    if not all([client_id, client_secret, redirect_uri, refresh_token]):
        raise ValueError('Faltan credenciales en .env')

    # Gestión de OAuth
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope='playlist-modify-public',
        cache_path='.cache',
        show_dialog=False
    )

    # Refrescar el access token usando el refresh_token existente
    token_info = sp_oauth.refresh_access_token(refresh_token)
    # Guardar token completo en caché para futuras llamadas
    sp_oauth.cache_handler.save_token_to_cache(token_info)

    # Crear cliente de Spotify autenticado
    return spotipy.Spotify(auth_manager=sp_oauth)


def get_user_id(sp: spotipy.Spotify) -> str:
    """Devuelve el user_id del usuario actual."""
    return sp.current_user()['id']


def get_or_create_playlist(sp: spotipy.Spotify, user_id: str, name: str) -> str:
    """
    Busca una playlist pública por nombre exacto; si no existe, la crea.
    Retorna el ID de la playlist.
    """
    playlists = sp.current_user_playlists(limit=50)
    for pl in playlists['items']:
        if pl['name'] == name:
            return pl['id']
    created = sp.user_playlist_create(user=user_id, name=name, public=True)
    return created['id']


def fetch_new_releases(sp: spotipy.Spotify, config: dict) -> list:
    """
    Recupera álbumes nuevos según ventana de meses y mercado configurados.
    """
    releases = sp.new_releases(limit=50, country=config.get('market', ''))
    cutoff = datetime.datetime.utcnow() - relativedelta(months=config['window_months'])
    return [alb for alb in releases['albums']['items']
            if datetime.datetime.strptime(alb['release_date'], '%Y-%m-%d') >= cutoff]


def get_tracks_from_albums(sp: spotipy.Spotify, albums: list) -> list:
    """
    Extrae tracks de una lista de álbumes.
    """
    tracks = []
    for alb in albums:
        items = sp.album_tracks(alb['id'])['items']
        for t in items:
            t['album_release_date'] = alb['release_date']
            tracks.append(t)
    return tracks


def filter_tracks(sp: spotipy.Spotify, tracks: list, genres: list, artists: list, config: dict) -> list:
    """
    Filtra tracks según géneros, artistas seleccionados y popularidad.
    Retorna lista de URIs únicas.
    """
    uris = []
    for t in tracks:
        track_meta = sp.track(t['id'])
        art_ids = [a['id'] for a in track_meta['artists']]
        art_data = sp.artists(art_ids)['artists']
        art_genres = set(g for ad in art_data for g in ad['genres'])
        name_match = any(ad['name'] in artists for ad in art_data)
        genre_match = bool(art_genres.intersection(genres))
        if (name_match or genre_match) and track_meta['popularity'] >= config['popularity_threshold']:
            uris.append(track_meta['uri'])
    # Eliminar duplicados manteniendo orden
    return list(dict.fromkeys(uris))


def get_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list:
    """
    Retorna lista de URIs de tracks actuales en la playlist.
    """
    uris = []
    results = sp.playlist_items(playlist_id, fields='items.track.uri,total', additional_types=['track'])
    for item in results['items']:
        uris.append(item['track']['uri'])
    return uris


def remove_old_tracks(sp: spotipy.Spotify, playlist_id: str, current_uris: list, valid_uris: list) -> list:
    """
    Elimina de la playlist tracks que ya no estén en valid_uris.
    """
    to_remove = [uri for uri in current_uris if uri not in valid_uris]
    if to_remove:
        sp.playlist_remove_all_occurrences_of_items(playlist_id, to_remove)
    return to_remove


def add_new_tracks(sp: spotipy.Spotify, playlist_id: str, valid_uris: list, current_uris: list, config: dict) -> list:
    """
    Añade a la playlist new_uris hasta completar el tamaño configurado.
    """
    new_candidates = [uri for uri in valid_uris if uri not in current_uris]
    space = config['playlist_size'] - len(current_uris)
    to_add = new_candidates[:space]
    if to_add:
        sp.playlist_add_items(playlist_id, to_add)
    return to_add


def update_playlist_flow(genres: list, artists: list, config_path: str = 'config.json') -> dict:
    """
    Orquesta el flujo completo de actualización de la playlist.
    Devuelve un resumen con conteos de adiciones y eliminaciones.
    """
    config = load_config(config_path)
    sp = init_spotify_client()
    user_id = get_user_id(sp)
    now = datetime.datetime.utcnow()
    name = config['name_template'].format(month=now.strftime('%B'), year=now.year)
    pid = get_or_create_playlist(sp, user_id, name)
    albums = fetch_new_releases(sp, config)
    tracks = get_tracks_from_albums(sp, albums)
    valid_uris = filter_tracks(sp, tracks, genres, artists, config)
    current_uris = get_playlist_tracks(sp, pid)
    removed = remove_old_tracks(sp, pid, current_uris, valid_uris)
    added = add_new_tracks(sp, pid, valid_uris, current_uris, config)
    return {
        'playlist_id': pid,
        'name': name,
        'added_count': len(added),
        'removed_count': len(removed)
    }

