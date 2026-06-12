from .base import *
from socket import gethostbyname, gethostname

DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
ALLOWED_HOSTS.append(gethostbyname(gethostname()))
SECRET_KEY = os.getenv('SECRET_KEY', 'production secret key')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

CELERY_BROKER_URL = os.getenv("CELERY_BORKER_URL", 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", 'redis://localhost:6379/0')