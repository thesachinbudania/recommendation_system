from celery import Celery
import ssl
from django.conf import settings


app = Celery("movies")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

if not settings.DEBUG:
    app.conf.broker_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
    }
    app.conf.redis_backend_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
    }