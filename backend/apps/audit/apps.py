from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit"

    def ready(self) -> None:
        # Registering the signal receivers is the whole point of this app, so it
        # happens on startup rather than on first import of a model.
        from . import signals  # noqa: F401
