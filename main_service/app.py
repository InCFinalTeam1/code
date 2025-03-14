from app import create_app
from app.extensions import socketio
from flask import *

app = create_app()

# 초기 화면
@app.route('/')
def index():
    return redirect(url_for('influ.influ'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)