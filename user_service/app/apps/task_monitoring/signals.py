from celery.signals import task_success, task_failure

from .models import TaskExecution


def _safe_str(value, limit=3000):
    return str(value)[:limit] if value is not None else None


@task_success.connect
def log_task_success(sender=None, result=None, **kwargs):
    request = sender.request
    print(request)
    TaskExecution.objects.update_or_create(
        task_id=request.id,
        defaults={
            "task_name": sender.name,
            "status": TaskExecution.Status.SUCCESS,
            "args": list(request.args) if request.args else None,
            "kwargs": request.kwargs or None,
            "result": _safe_str(result),
            "retries": request.retries,
        },
    )


@task_failure.connect
def log_task_failure(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    einfo=None,
    **extra
):
    TaskExecution.objects.update_or_create(
        task_id=task_id,
        defaults={
            "task_name": sender.name if sender else "unknown",
            "status": TaskExecution.Status.FAILED,
            "args": list(args) if args else None,
            "kwargs": kwargs or None,
            "result": _safe_str(exception),
            "traceback": _safe_str(einfo, limit=6000),
            "retries": sender.request.retries if sender else 0,
        },
    )
