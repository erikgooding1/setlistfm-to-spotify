import subprocess
import json
from flask import Flask, request, render_template

app = Flask(__name__)

subprocess_raw = 'output/subprocess_raw.json'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        return render_template('loading.html', url=url)
    else:
        return '''
            <form method="post">
                <label for="url">Enter URL:</label>
                <input type="text" id="url" name="url">
                <input type="submit" value="Execute Script">
            </form>
        '''

@app.route('/execute', methods=['POST'])
def execute():
    url = request.form['url']

    output = subprocess.run(['python', 'generate-setlist.py', url], stdout=subprocess.PIPE, universal_newlines=True)
    return render_template('output.html', output=output.stdout)

if __name__ == '__main__':
    app.run(debug=True)