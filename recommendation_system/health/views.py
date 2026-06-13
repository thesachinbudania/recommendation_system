from django.db import connections
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from health.tasks import celery_ping_task



def liveness(request):
    return JsonResponse({"status": "alive"})

def readiness(request):
    status = {
        "database": "unhealthy",
        "s3storage": "unhealthy",
        "celery": "unhealthy"
    }
    try:
        connections["default"].cursor()
        status['database'] = "healthy"
        file_path = default_storage.save("health/readiness.txt", ContentFile(b'This is readiness test file'))
        default_storage.delete(file_path)
        status['s3storage'] = "healthy"
        async_result = celery_ping_task.apply_async()
        outcome = async_result.get(timeout=10)
        if outcome == "pong":
            status['celery'] = "healthy"
    except:
        pass
    if all(value == 'healthy' for value in status.values()):
        return JsonResponse({"status": "healthy", "results": status}, status=200)
    else:
        return JsonResponse({"status": "unhealthy", "results": status}, status=500)
