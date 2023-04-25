from app import app
import openai, os
from flask import render_template, url_for, session, redirect, request
from flask_session import Session
from google.cloud import firestore
from datetime import date

from dotenv import load_dotenv
load_dotenv()

import spotipy
today = date.today()

db = firestore.Client(project=os.getenv("GCP_PROJECT_ID"))
# sessions = db.collection('sessions')

@app.route('/')
def index():

    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(scope='user-read-currently-playing playlist-modify-private user-top-read user-read-recently-played',
                                               cache_handler=cache_handler,
                                               show_dialog=True)

    if request.args.get("code"):
        # Step 2. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        spotify = spotipy.Spotify(auth_manager=auth_manager)
        user = spotify.me()
        session['current_user'] = user['display_name'] 
        return redirect('/')

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 1. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()

        return render_template('index.html', auth_url=auth_url)        

    # Step 3. Signed in, display data
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    me = spotify.me()
    doc_ref = db.collection(u'users').document(me['id'])
    doc_ref.set(me)

    return render_template('index.html', user=spotify.me())    

@app.route('/sign-out')
def sign_out():
    session.pop("token_info", None)
    session.pop("current_user", None)
    return redirect('/')


@app.route('/my-playlists')
def my_playlists():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')

    spotify = spotipy.Spotify(auth_manager=auth_manager)
    results = spotify.current_user_playlists()


    write_user_collections(spotify.me()['id'], 'my-playlists', results) 
    
   
    return render_template('my_playlists.html', user=spotify.me(), results=results)

@app.route('/recently-played')
def following_playlists():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')

    spotify = spotipy.Spotify(auth_manager=auth_manager)
    results =spotify.current_user_recently_played()    

    write_user_collections(spotify.me()['id'], 'recently-played', results) 

    return render_template('recently_played.html', user=spotify.me(), results=results)

@app.route('/profile')
def profile():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)    
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    return render_template('profile.html', user=spotify.me())


@app.route('/top-artists')
def top_tracks():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    ranges = ['short_term']
    results = spotify.current_user_top_artists(time_range=ranges, limit=50)
    print(results)
    if spotify.me():
        user = spotify.me()
    else: None

    write_user_collections(spotify.me()['id'], 'top-artists', results) 

    return render_template('top_artists.html', results=results, user=user )

@app.route('/create-playlist')
# TODO this doesn't work yet
# pipe the GPT track output list into the search function below
def create_playlist():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    spotify = spotipy.Spotify(auth_manager=auth_manager) 

    spotify = spotipy.Spotify(auth_manager=auth_manager)
    me = spotify.me()
    
    tracks = request.args.getlist("track")
    playlist = spotify.user_playlist_create(user=me['id'], name="Musicmap Playlist")        
    spotify.user_playlist_add_tracks(user=me['id'], playlist_id=playlist['id'], tracks=tracks)
    
    return render_template('top_artists.html', results=results, user=user )

# def search_spotify_track_uris(tracks):

@app.route('/current_user')
def current_user():
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    return spotify.current_user()

def write_user_collections(user_id, collection_name, results):
    today_timestamp = today.strftime("%Y-%m-%d")
    base_doc = db.collection(u'listen-timeseries').document(user_id)
    doc = base_doc.collection(today_timestamp).document(collection_name)
    doc.set(results)

@app.route("/get-similar-songs")
def get_similar_songs():
    print(os.getenv("OPENAI_API_KEY"))
    openai.api_key = os.getenv("OPENAI_API_KEY")

    band = request.args.get("band")
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt="return a comma separated list of 20 tracks similar to the band {}".format(band),
        max_tokens=1000,
        temperature=0.6,
    )

    print(response)

    return render_template('similar_songs.html', results=response.choices[0].text)









# FIRESTORE SESSION AUTH - CAN BE IMPLEMENTED LATER
# Need to just keep ONLY 1 cloud run instance for now...

# @firestore.transactional
# def get_session_data(transaction, session_id):
#     """ Looks up (or creates) the session with the given session_id.
#         Creates a random session_id if none is provided. Increments
#         the number of views in this session. Updates are done in a
#         transaction to make sure no saved increments are overwritten.
#     """
#     if session_id is None:
#         session_id = str(uuid4())   # Random, unique identifier

#     doc_ref = sessions.document(document_id=session_id)
#     doc = doc_ref.get(transaction=transaction)
#     if doc.exists:
#         session = doc.to_dict()
#     else:
#         session = {
#             'greeting': random.choice(greetings),
#             'views': 0
#         }

#     session['views'] += 1   # This counts as a view
#     transaction.set(doc_ref, session)

#     session['session_id'] = session_id
#     return session