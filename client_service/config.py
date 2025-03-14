# config.py
import os

class Config:
    AUTH_USERSERVICE_URL = os.getenv('AUTH_USERSERVICE_URL')
    AUTH_ANALYZE_URL = os.getenv('AUTH_ANALYZE_URL',"https://www.ssginc.store") ## 서비스
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    # AUTH_USERSERVICE_URL = os.getenv('AUTH_USERSERVICE_URL', 'http://user-service.default.svc.cluster.local:8001')