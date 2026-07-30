from django.apps import AppConfig


class TaskMonitoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.apps.task_monitoring"

    def ready(self):
        import app.apps.task_monitoring.signals
