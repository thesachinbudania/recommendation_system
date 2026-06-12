from django.db import connections
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.cache import cache

def liveness(request):
    return JsonResponse({"status": "alive"})

def readiness(request):
    try:
        connections["default"].cursor()
    except:
        return JsonResponse({"status": "unhealthy", "reason": "Unable to connect to database"},)
    try:
        file_path = default_storage.save("health/readiness.txt", ContentFile(b'This is readiness test file'))
        default_storage.delete(file_path)
    except:
        return JsonResponse({"status": "unhealthy", "reason": "Unable to connect to storage bucket."},
                                status=500)
    try:
        cache.set("health_check", "ok", timeout=10)
        if cache.get("healt_check") == "ok":
            return ValueError("Failed to communicate with cache backend")
    except:
        return JsonResponse({"status": "unhealthy", "reason": "Unable to communicate with cache backend."},)
    return JsonResponse({"status": "healthy"}, status=200)

