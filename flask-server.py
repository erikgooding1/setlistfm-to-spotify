import subprocess
import json
from flask import Flask, request, render_template

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        if request.form.get('tapes') == 'on':
            tapes = 'true'
        else:
            tapes = 'false'
        if request.form.get('medleys') == 'on':
            medleys = 'true'
        else:
            medleys = 'false'

        return render_template('loading.html', url=url, tapes=tapes, medleys=medleys)
    else:
        return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    url = request.form.get('url')
    tapes = request.form.get('tapes')
    medleys = request.form.get('medleys')

    output = subprocess.run(['python', 'generate-setlist.py', url, tapes, medleys], stdout=subprocess.PIPE, universal_newlines=True)
    output_as_string = output.stdout
    lines = output_as_string.split('\n')
    if lines[0] == 'Playlist created':
        playlist_link = lines[1]
        print(playlist_link)
        embed_code = f'<iframe src="https://open.spotify.com/embed/playlist/{playlist_link.split(":")[2]}" width="300" height="380" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>'
        return render_template('output.html', embed_code=embed_code)
    else:
        warning = f'<div id="warning" class="alert alert-warning m-3" role="alert">{lines[0]}</div>'
        return render_template('index.html', warning=warning)


if __name__ == '__main__':
    app.run(debug=True)