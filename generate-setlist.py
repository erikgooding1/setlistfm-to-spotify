import sys
import os
import json
import re
import requests
import asyncio
import spotipy
import logging
import base64
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv, set_key

load_dotenv("./.env")

logging.basicConfig(level=logging.INFO)

# SPOTIFY API https://developer.spotify.com/documentation/web-api
# SETLIST.FM API https://api.setlist.fm/docs/1.0/index.html
# SPOTIPY API https://spotipy.readthedocs.io/en/2.22.1/

# CURRENT STATUS:
# Can retrieve setlist from setlist.fm, and get artist name, as well as song names
# Can retrieve artist info from spotify, and get artist name, genres, popularity, and followers
# Reauthorize API if token expires
# For each track in setlist, can see if an exact match of the track exists in spotify under the given artist, or an exact match under a cover artist
# Can create a playlist with the name of the artist and tour name, and add all the tracks to it

# TODO:
# Figure out how to get the track id of a song if it is not an exact match


SETLIST_LINK = "https://www.setlist.fm/setlist/uicideboy/2023/state-farm-arena-atlanta-ga-2ba50c6a.html"
SETLIST_FM_API_LINK = "https://api.setlist.fm/rest/1.0/setlist/"
SETLIST = []
SETLIST_ARTIST = []
SETLIST_SONG_IDS = []
TOUR = {}

ARTIST = {}
ARTIST_FILE = "output/setlistArtistDetails.json"
SETLIST_RAW_FILE = "output/rawsetlistfmresponse.json"

username = sys.argv[4]
access_token = sys.argv[5]
refresh_token = sys.argv[6]


try:
    #sp_oauth = SpotifyOAuth(client_id=os.environ['CLIENT_ID'], client_secret=os.environ['CLIENT_SECRET'], redirect_uri="https://spotify-setlist.egood.tech/callback", username=username, refresh_token=refresh_token,  scope="playlist-modify-public user-library-read user-library-modify ugc-image-upload", open_browser=False)
    #token_info = sp_oauth.get_access_token(code=None)

    spotify = spotipy.Spotify(auth=access_token, requests_timeout=10, retries=10)

    library = spotify.current_user_saved_tracks()
    profile = spotify.current_user()
except:
    print("Something went wrong with spotify")

async def getSetlist(setlistLink):


    REQ_HEADERS = {
        "x-api-key": os.environ['SETLIST_KEY'],
        "Accept": "application/json"
        }
    SETLIST_FILE = "output/setlist.json"

    pattern = r"(\w+).html$"
    setlist_id = re.findall(pattern, setlistLink)[0]

    logging.info(setlist_id)
    REQ_LINK = SETLIST_FM_API_LINK + setlist_id

    # Get request to setlist.fm API
    try:
        response = requests.get(REQ_LINK, headers=REQ_HEADERS)
        responseJson = response.json()

        with open(SETLIST_RAW_FILE, 'w') as outfile:
            json.dump(responseJson, outfile, indent=2)

        SETLIST_ARTIST.append(responseJson["artist"]["name"])

        TOUR["venue"] = responseJson["venue"]["name"]
        TOUR["city"] = responseJson["venue"]["city"]["name"]
        TOUR["country"] = responseJson["venue"]["city"]["country"]["code"]
        TOUR["year"] = responseJson["eventDate"][-4:]
        if "tour" in responseJson:
            TOUR["name"] = responseJson["tour"]["name"]

        # Pattern to see if a song is a medley (separated by ' / ')
        medleyPattern = r"\s\/\s"

        for song in responseJson["sets"]["set"][0]["song"]:
            # For each song in the setlist.fm setlist, check if it is a medley
            medleyMatch = re.search(medleyPattern, song['name'])
            if medleyMatch != None:
                logging.info("Medley found!")

                # If the medley checkbox isn't selected, omit it from the spotify setlist
                if sys.argv[3] == 'false':
                    logging.info("Omitting medley")
                    continue
                else:
                    # If the medley checkbox is selected, add each song in the medley to the spotify setlist
                    # This assumes that all songs in a medley is by the touring artist, and not a cover
                    medleySongs = song['name'].split(" / ")
                    for medleySong in medleySongs:
                        SETLIST.append([medleySong, responseJson["artist"]["name"], False, 'tape' in song])
            else:
                try: 
                    # if the song is a cover, add the original artists song to the  spotify setlist
                    SETLIST.append([song["name"], song['cover']['name'], True, 'tape' in song])
                except KeyError:
                    # if the song is not a cover, add the song to the spotify setlist
                    SETLIST.append([song["name"], responseJson["artist"]["name"], False, 'tape' in song])

        try:
            # Encore songs are kept in a different part of the json response from setlist.fm.
            # If an encore exists, add it to the spotify setlist
            if responseJson["sets"]["set"][1]:
                for song in responseJson["sets"]["set"][1]["song"]:
                    try: 
                        SETLIST.append([song["name"], song['cover']['name'], True, 'tape' in song])
                    except KeyError:
                        SETLIST.append([song["name"], responseJson["artist"]["name"], False, 'tape' in song])
        except:
            logging.info("No encore found")
        
            
    except requests.exceptions.HTTPError as err:
        logging.info('Error:', err.response.status_code)
        print('Error:', err.response.status_code)
        sys.exit()

async def getArtistSpotifyDetails(artistName):
    global ARTIST

    artistSearchResults = spotify.search(q='artist:'+artistName, type='artist')
    artistID = artistSearchResults["artists"]["items"][0]["id"]
    ARTIST = spotify.artist(artistID)

    logging.info(f"Artist name: {ARTIST['name']}")
    logging.info(f"Artist genres: {', '.join(ARTIST['genres'])}")
    logging.info(f"Artist popularity: {ARTIST['popularity']}")
    logging.info(f"Artist followers: {ARTIST['followers']['total']}")

    with open(ARTIST_FILE, 'w') as outfile:
        json.dump(artistSearchResults, outfile, indent=2)

async def getTrackIds(setlist):
    numSongs = 0
    for i, track in enumerate(setlist):
        logging.info(track)
        try:
            # If the track is a tape, and tapes are not selected, skip the track
            if track[3] == True and sys.argv[2] == 'false':
                logging.info(f"Skipping {track[0]} because it is a tape")
                continue
            else:
                trackData = await getTrack(track[0], track[1], track[2])
                SETLIST_SONG_IDS.append(trackData["id"])
                logging.info(f"Track {numSongs+1} | ID: {trackData['id']} | Name: {trackData['name']}")
                numSongs += 1
        except:
            continue

async def getTrack(track, artist, isCover):
    query = f"track:{track} artist:{artist}"
    try:
        trackSearchResults = spotify.search(q=query, type='track')
        filteredTracks = [track for track in trackSearchResults['tracks']['items'] if track['explicit'] == True]
        return trackSearchResults['tracks']['items'][0]
    except:
        # Reattempt to find track with the touring artist's name rather than the cover artist's name
        if isCover:
            try:
                query = f"track:{track} artist:{SETLIST_ARTIST[0]}"
                trackSearchResults = spotify.search(q=query, type='track')
                return trackSearchResults['tracks']['items'][0]
            except:
                logging.info(f"Could not find {track} by {SETLIST_ARTIST[0]}")
                return None
        else:
            logging.info(f"Could not find {track} by {artist}")
            return None

async def createPlaylist(setlistSongIDs):
    
    if "name" in TOUR:
        playlist_name = f'{SETLIST_ARTIST[0]} Setlist - {TOUR["name"]} - ({TOUR["year"]})'
        playlist_description = f'{SETLIST_ARTIST[0]} - {TOUR["name"]} Setlist'
    else:
        playlist_name = f'{SETLIST_ARTIST[0]} Setlist - {TOUR["venue"]}, {TOUR["city"]}, {TOUR["country"]} ({TOUR["year"]})'
        playlist_description = f"{SETLIST_ARTIST[0]} Setlist"



    playlist = spotify.user_playlist_create(profile["id"], playlist_name, public=True, collaborative=False, description=playlist_description)
    spotify.user_playlist_add_tracks(profile["id"], playlist["id"], setlistSongIDs)

    artist_image = await get_as_base_64(ARTIST["images"][0]["url"])
    spotify.playlist_upload_cover_image(playlist["id"], artist_image)

    logging.info(f"You have added {len(setlistSongIDs)} songs to your playlist {playlist_name}")
        #playlist_details = spotify.playlist(playlist_id=playlist["id"])
    playist_uri = playlist["uri"]
    logging.info("Playlist URI: " + playist_uri)
    print("Playlist created")
    print(playist_uri)

# helper function to encode first artist image as base64
async def get_as_base_64(url):
    return base64.b64encode(requests.get(url).content).decode('utf-8')

if len(sys.argv) > 1:
    SETLIST_LINK = sys.argv[1]

validSetlist = re.search(r'https://www.setlist.fm/setlist/.*', SETLIST_LINK)
logging.info(sys.argv)
if sys.argv[2] == 'true':
    logging.info("Tapes selected")
else:
    logging.info("No tapes selected")

if sys.argv[3] == 'true':
    logging.info("Medleys selected")
else:
    logging.info("No medleys selected")

if not validSetlist:
    logging.info("Invalid setlist link")
    print("Invalid setlist link provided. Example: https://www.setlist.fm/setlist/muse/2023/the-o2-arena-london-england-6ba3d6fe.html")
    sys.exit()
else :
    asyncio.run(getSetlist(SETLIST_LINK))
    logging.info(SETLIST_ARTIST)
###############
asyncio.run(getArtistSpotifyDetails(SETLIST_ARTIST[0]))

asyncio.run(getTrackIds(SETLIST))

asyncio.run(createPlaylist(SETLIST_SONG_IDS))

###############


