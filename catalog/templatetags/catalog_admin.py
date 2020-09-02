from django.urls import reverse
from django.template import Library
from catalog.utils import get_catalog_models

register = Library()


@register.inclusion_tag('admin/catalog/include/add_btns.html')
def add_btns():
    """
    Get add object buttons for every registered catalog models
    """
    models_info = []
    for model in get_catalog_models():
        model_name = model.__name__
        if model._meta.verbose_name:
            model_name = model._meta.verbose_name

        models_info.append([reverse('admin:{0}_{1}_add'. \
                                    format(model._meta.app_label,
                                           model._meta.model_name)),
                            model_name])
    return {'models_info': models_info, }