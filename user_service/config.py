# config.py
import os

class Config:
    AUTH_MAINSERVICE_URL = os.getenv('AUTH_MAINSERVICE_URL',"https://www.ssginc.store") ## 서비스
    # AUTH_MAINSERVICE_URL = os.getenv('AUTH_MAINSERVICE_URL', 'http://0.0.0.0:8000') ## 서비스
    # AUTH_MAINSERVICE_URL = os.getenv('AUTH_MAINSERVICE_URL') ## 서비스
    AUTH_CLIENTSERVICE_URL = os.getenv('AUTH_CLIENTSERVICE_URL',"https://www.ssginc.store") ## 서비스
    AUTH_ANALYZE_URL = os.getenv('AUTH_ANALYZE_URL',"https://www.ssginc.store") ## 서비스
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")