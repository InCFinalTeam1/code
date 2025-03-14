from flask import Flask
from config import Config
# from app.extensions import socketio

from app.client import blueprint as client_blueprint

def create_app():
    app = Flask(__name__)
    app.secret_key = 'bsdajvkbakjbfoehihewrpqkldn21pnifninelfbBBOIQRqnflsdnljneoBBOBi2rp1rp12r9uh'
    app.config.from_object(Config)

    # 블루프린트 등록
    app.register_blueprint(client_blueprint)

    return app