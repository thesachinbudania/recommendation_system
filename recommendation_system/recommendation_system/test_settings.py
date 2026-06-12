from .base import *

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': BASE_DIR / 'test_db.sqlite3',
	}
}

AWS_ACCESS_KEY_ID = 'minio-admin'
AWS_SECRET_ACCESS_KEY = 'minio-admin'
AWS_STORAGE_BUCKET_NAME = 'test-bucket'
AWS_S3_ENDPOINT_URL = 'http://localhost:9000'
AWS_S3_CUSTOM_DOMAIN = 'localhost:9000'
AWS_S3_USE_SSL = "True"

SECRET_KEY = 'test-secret-key'