from spotify_helper import init_spotify_client

def test_connection():
    try:
        sp = init_spotify_client()
        me = sp.me()  # solicita información del usuario actual
        print("✅ Conexión exitosa a Spotify")
        print(f"Usuario autenticado: {me.get('display_name', 'Desconocido')}")
    except Exception as e:
        print("❌ No se pudo conectar a la API de Spotify")
        print(f"Error: {e}")


if __name__ == "__main__":
    test_connection()
