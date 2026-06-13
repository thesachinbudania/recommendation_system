from celery import shared_task

@shared_task(name="health_check")
def celery_ping_task():
    return "pong"
