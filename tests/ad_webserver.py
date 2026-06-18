from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {
                margin: 0;
                padding: 0;
            }
            html, body {
                width: 100%;
                height: 100%;
                overflow: hidden;
            }
            .container {
                width: 300px;
                height: 250px;
                background-color: gray;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="container" onclick="window.open('https://naver.com', '_blank');"></div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True)
