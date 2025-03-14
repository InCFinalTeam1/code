from app import *
from app.extensions import socketio
from flask import *
from flask_session import Session
import redis
import os
from config import Config
# REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

app = create_app()

# Redis 세션 저장소 설정
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
# app.config['SESSION_REDIS'] = redis.from_url('redis://redis-cluster-master.redis.svc.cluster.local:6379')
# app.config['SESSION_REDIS'] = redis.from_url(f'redis://:{Config.REDIS_PASSWORD}@redis-cluster-master.default.svc.cluster.local:6379')

server_session = Session(app)

# 헬스체크 엔드포인트
@app.route('/healthz')
def health_check():
    # 필요한 경우, 추가적인 체크 (예: Redis 연결 확인 등)을 할 수 있음
    return 'OK', 200

# 초기 화면
@app.route('/')
def index():
    print(1)
    return redirect(url_for('influ.influ'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)
