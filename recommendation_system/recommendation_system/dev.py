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

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_SIGNATURE_NAME = 's3v4'
AWS_S3_REGION_NAME = 'ap-south-1'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_S3_VERITY = True

