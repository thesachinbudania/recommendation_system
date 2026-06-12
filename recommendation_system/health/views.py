from django.db import connections
from django.http import JsonResponse

def liveness(request):
    return JsonResponse({"status": "alive"})

def readiness(request):
    try:
        connections["default"].cursor()
        return JsonResponse({"status": "healthy"}, status=200)
    except:
        return JsonResponse({"status": "unhealthy"}, status=500)