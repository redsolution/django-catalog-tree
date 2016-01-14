from django.contrib.sitemaps import GenericSitemap
from django.db.models import FieldDoesNotExist
from utils import get_catalog_models


class CatalogSitemap(GenericSitemap):
    def __init__(self, model, priority=None, changefreq=None):
        info_dict = {
            'queryset': model.objects.filter(show=True)
        }
        try:
            model._meta.get_field_by_name('last_modified')
        except FieldDoesNotExist:
            pass
        else:
            info_dict['date_field'] = 'last_modified'
        super(CatalogSitemap, self).__init__(
            info_dict=info_dict, priority=priority, changefreq=changefreq)


def get_sitemaps():
    """
    :return: Dictionary with `CatalogSitemap` for each registered model.
    """
    sitemaps = {}
    for model in get_catalog_models():
        try:
            model._meta.get_field_by_name('slug')
        except FieldDoesNotExist:
            pass
        else:
            sitemaps['{0}.{1}'.format(model._meta.app_label,
                                      model._meta.module_name)] = \
                CatalogSitemap(model)
    return sitemaps