from app import create_app
from flask import *

app = create_app()

# 초기 화면
@app.route('/')
def index():
    return redirect(url_for('client.clientpage'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)