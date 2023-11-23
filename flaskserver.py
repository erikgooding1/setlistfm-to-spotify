import subprocess
import json
import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, render_template, session, redirect, url_for
from dotenv import load_dotenv, set_key

load_dotenv("./.env")

app = Flask(__name__)
app.secret_key = 'xyz'

CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
REDIRECT_URI = "https://spotify-setlist.egood.tech/callback" 
SCOPE = ["playlist-modify-public", "user-library-read", "user-library-modify", "ugc-image-upload"]
SCOPE_STRING = " ".join(SCOPE)

sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope=SCOPE)

AUTH_URL = f"https://accounts.spotify.com/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={' '.join(SCOPE)}"
TOKEN_URL = "https://accounts.spotify.com/api/token" # The Spotify token URL


@app.route('/', methods=['GET', 'POST'])
def index():
    #if 'username' in session:
        #return f"Logged in as {session['username']}"
    if request.method == 'POST' and 'username' in session:
        url = request.form['url']
        if request.form.get('tapes') == 'on':
            tapes = 'true'
        else:
            tapes = 'false'
        if request.form.get('medleys') == 'on':
            medleys = 'true'
        else:
            medleys = 'false'

        return render_template('loading.html', url=url, tapes=tapes, medleys=medleys, username=session['username'], access_token=session['access_token'], refresh_token=session['refresh_token'])
    elif request.method == 'POST' and 'username' not in session:
        auth_session_html=f'<form class="mb-3" action="https://accounts.spotify.com/authorize" method="GET"><input type="hidden" name="client_id" value="{ CLIENT_ID }"><input type="hidden" name="response_type" value="code"><input type="hidden" name="redirect_uri" value="{ REDIRECT_URI }"><input type="hidden" name="scope" value="{ SCOPE_STRING }"><input type="submit" value="Authorize"></form>'
        return render_template('index.html', auth_html = auth_session_html, client_id = CLIENT_ID, response_type = "code", redirect_uri = REDIRECT_URI, scope = SCOPE_STRING, warning="Please first authorize us to generate a playlist on your Spotify account.")
    else:
        if 'username' not in session: 
            auth_session_html=f'<form class="mb-3" action="https://accounts.spotify.com/authorize" method="GET"><input type="hidden" name="client_id" value="{ CLIENT_ID }"><input type="hidden" name="response_type" value="code"><input type="hidden" name="redirect_uri" value="{ REDIRECT_URI }"><input type="hidden" name="scope" value="{ SCOPE_STRING }"><input type="submit" value="Authorize"></form>'
            return render_template('index.html', auth_html=auth_session_html, client_id = CLIENT_ID, response_type = "code", redirect_uri = REDIRECT_URI, scope = SCOPE_STRING)
        else:
            auth_session_html=f'<p>Logged in as { session["display_name"] }</p>'
            return render_template('index.html', auth_html=auth_session_html, client_id = CLIENT_ID, response_type = "code", redirect_uri = REDIRECT_URI, scope = SCOPE_STRING)

@app.route('/callback')
def callback():
    print("callback")
    code = request.args.get("code")
    if code:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
       }

        response = requests.post(TOKEN_URL, data=payload)
        data = response.json()

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        if access_token and refresh_token:
            sp = spotipy.Spotify(auth=access_token)
            user_info = sp.current_user()
            user_id = user_info['id']
            user_display_name = user_info['display_name']
            print(user_id)

            session['username'] = user_id
            session['display_name'] = user_display_name
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token

            auth_session_html=f'<p>Logged in as { session["display_name"] }</p>'
            return render_template('index.html', auth_html=auth_session_html, client_id = CLIENT_ID, response_type = "code", redirect_uri = REDIRECT_URI, scope = SCOPE_STRING)
        else:
            auth_session_html=f'<form class="mb-3" action="https://accounts.spotify.com/authorize" method="GET"><input type="hidden" name="client_id" value="{{ client_id }}"><input type="hidden" name="response_type" value="code"><input type="hidden" name="redirect_uri" value="{{ redirect_uri }}"><input type="hidden" name="scope" value="{{ scope }}"><input type="submit" value="Authorize"></form>'
            warning = f'<div id="warning" class="alert alert-warning m-3" role="alert">Could not authorize spotify account</div>'
            return render_template('index.html', auth_html=auth_session_html, client_id = CLIENT_ID, response_type = "code", redirect_uri = REDIRECT_URI, scope = SCOPE_STRING, warning=warning)

    else:
        auth_session_html = f'<form class="mb-3" action="https://accounts.spotify.com/authorize" method="GET"><input type="hidden" name="client_id" value="{{ client_id }}"><input type="hidden" name="response_type" value="code"><input type="hidden" name="redirect_uri" value="{{ redirect_uri }}"><input type="hidden" name="scope" value="{{ scope }}"><input type="submit" value="Authorize"></form>'
        return render_template("index.html", auth_html=auth_session_html, client_id = CLIENT_ID, response_type = "code", redirect-uri = REDIRECT_URI, scope = SCOPE_STRING)

@app.route('/execute', methods=['POST'])
def execute():
    url = request.form.get('url')
    tapes = request.form.get('tapes')
    medleys = request.form.get('medleys')
    username = request.form.get('username')
    access_token = request.form.get('access_token')
    refresh_token = request.form.get('refresh_token')
    domWidth = int(request.form.get('domWidth'))

    print(domWidth)
    if domWidth >= 992:
        iframeWidth = 900
        iframeHeight = 500
    elif domWidth >= 768:
        iframeWidth = 0.75 * domWidth
        iframeHeight = 500
    elif domWidth >= 576:
        iframeWidth = 0.75 * domWidth
        iframeHeight = 500
    else:
        iframeWidth = 0.75 * domWidth
        iframeHeight = 450


    output = subprocess.run(['python', 'generate-setlist.py', url, tapes, medleys, username, access_token, refresh_token], stdout=subprocess.PIPE, universal_newlines=True)
    output_as_string = output.stdout
    lines = output_as_string.split('\n')
    if lines[0] == 'Playlist created':
        playlist_link = lines[1]
        print(playlist_link)
        embed_code = f'<iframe src="https://open.spotify.com/embed/playlist/{playlist_link.split(":")[2]}" width="{iframeWidth}" height="{iframeHeight}" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>'
        return render_template('output.html', embed_code=embed_code)
    else:
        warning = f'<div id="warning" class="alert alert-warning m-3" role="alert">{lines[0]}</div>'
        return render_template('index.html', warning=warning)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
