from django.db import connections
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.cache import cache
from celery import shared_task

@shared_task(name="health_check")
def celery_ping_task():
    return "pong"

def liveness(request):
    return JsonResponse({"status": "alive"})

def readiness(request):
    status = {
        "database": "unhealthy",
        "s3storage": "unhealthy",
        "cache": "unhealthy",
        "celery": "unhealthy"
    }
    try:
        connections["default"].cursor()
        status['database'] = "healthy"
        file_path = default_storage.save("health/readiness.txt", ContentFile(b'This is readiness test file'))
        default_storage.delete(file_path)
        status['s3storage'] = "healthy"
        cache.set("health_check", "ok", timeout=10)
        if cache.get("health_check") == "ok":
            status['cache'] = "healthy"
        async_result = celery_ping_task.apply_async()
        outcome = async_result.get(timeout=5)
        if outcome == "pong":
            status['celery'] = "healthy"
    except:
        pass
    if all(value == 'healthy' for value in status.values()):
        return JsonResponse({"status": "healthy", "results": status}, status=200)
    else:
        return JsonResponse({"status": "unhealthy", "results": status}, status=500)
