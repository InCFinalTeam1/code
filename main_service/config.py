# config.py
import os

class Config:
    # AUTH_USERSERVICE_URL = os.getenv('AUTH_USERSERVICE_URL', 'http://0.0.0.0:8001')
    AUTH_USERSERVICE_URL = os.getenv('AUTH_USERSERVICE_URL',"https://www.ssginc.store")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    
    print(f"AUTH_USERSERVICE_URL: {AUTH_USERSERVICE_URL}")  