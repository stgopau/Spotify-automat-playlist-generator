# 🎧 Spotify Automat Playlist Generator

Automatizador para generar playlists de Spotify usando la API oficial.  
Este proyecto permite:

- Buscar artistas  
- Administrar un *pool* de artistas  
- Generar recomendaciones personalizadas  
- Crear y reemplazar playlists en tu cuenta  
- Guardar datos localmente  
- Ejecutar funciones desde un menú interactivo

Este repositorio está pensado para ejecutarse desde terminal como herramienta utilitaria.

---

## 🧰 Tecnologías utilizadas

- **Python 3.10+**
- **Spotify Web API**
- **requests**
- **dotenv** para variables secretas
- Scripts CLI con módulos propios del proyecto

---

# 🚀 Instalación

## 1. Clonar el repositorio

```bash
git clone https://github.com/stgopau/Spotify-automat-playlist-generator.git
cd Spotify-automat-playlist-generator
```

## 2. Crear un entorno virtual (recomendado)
```bash
python3 -m venv venv
source venv/bin/activate     # macOS / Linux
venv\Scripts\activate        # Windows
```

## 3. Instalar dependencias
```bash
pip freeze > requirements.txt
pip install -r requirements.txt
```

# 🔑 Configuración de Spotify (muy importante)
## 1. Crear una app en Spotify Developer

Ve a https://developer.spotify.com/dashboard

Inicia sesión

Crea una nueva aplicación

Copia:
- Client ID
- Client Secret

En Redirect URIs, agrega:
```bash
http://localhost:8888/callback
```

# 🔧 Variables de entorno

Crea un archivo .env en la raíz del proyecto:
```bash
SPOTIFY_CLIENT_ID=tu_client_id
SPOTIFY_CLIENT_SECRET=tu_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

# 🗂️ Estructura del proyecto
Spotify-automat-playlist-generator/
│
├── spotify_helper.py          
├── auth_tokens.py
├── get_refresh_token.py       
├── main_menu.py               
├── search_artists.py          
├── select_and_pool.py         
├── generate_recs.py           
├── create_playlist.py         
├── replace_playlist.py        
├── list_playlists.py          
│
├── artists.json               
├── playlist_recs.json         
├── config.json                
│
├── .env.example               
├── .gitignore
└── README.md

# ▶️ Ejecución del proyecto
## 1. Activar el entorno virtual
```bash
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate       # Windows
```

## 2. Obtener el token inicial (solo la primera vez)
```bash
python get_refresh_token.py
```

# 💾 Archivo .env.example
```bash
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```
