import subprocess
import json
from flask import Flask, request, render_template

app = Flask(__name__)

subprocess_raw = 'output/subprocess_raw.json'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        print(url)
        return render_template('loading.html', url=url)
    else:
        return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    url = request.form['url']

    
    playlist_link = subprocess.run(['python', 'generate-setlist.py', url], stdout=subprocess.PIPE, universal_newlines=True)
    if playlist_link.stdout == "Playlist creation cancelled\n":
        warning = f'<div id="warning" class="alert alert-warning" role="alert">This is a warning alert—check it out!</div>'
        return render_template('index.html', warning=warning)
    else:
        embed_code = f'<iframe src="https://open.spotify.com/embed/playlist/{playlist_link.stdout.split(":")[2]}" width="300" height="380" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>'
    #print(embed_code)
        return render_template('output.html', embed_code=embed_code)

if __name__ == '__main__':
    app.run(debug=True)