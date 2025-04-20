import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def get_spotify_client():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET is not set in the environment.")

    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth_manager)
