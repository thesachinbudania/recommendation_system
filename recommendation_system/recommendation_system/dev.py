from .base import *
from socket import gethostname, gethostbyname

DEBUG = True
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", 'localhost,127.0.0.1').split(",")
ALLOWED_HOSTS.append(gethostbyname(gethostname()))
SECRET_KEY = os.getenv('SECRET_KEY', "development_env")
CORS_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
]