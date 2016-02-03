from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CatalogAppConfig(AppConfig):
    name = 'catalog'
    verbose_name = _('Catalog')


# class for custom catalog models
class CustomCatalogBaseConfig(AppConfig):

    def ready(self):
        import signals