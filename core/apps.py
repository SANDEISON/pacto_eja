from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Painel"

    def ready(self):
        """Registra os signals assim que a aplicação Django estiver pronta."""
        from . import signals  # noqa: F401  # A importação executa o registro dos handlers.
