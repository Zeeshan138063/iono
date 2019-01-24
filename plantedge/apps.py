from django.apps import AppConfig


class PlantedgeConfig(AppConfig):
    name = 'plantedge'

    def ready(self):
        import plantedge.signals  # noqa