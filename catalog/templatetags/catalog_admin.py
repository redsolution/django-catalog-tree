from django.core.urlresolvers import reverse
from django.template import Library
from catalog.utils import get_catalog_models

register = Library()


@register.inclusion_tag('catalog/admin/include/add_btns.html')
def add_btns():
    models_info = []
    for model in get_catalog_models():
        model_name = model.__name__
        if model._meta.verbose_name:
            model_name = model._meta.verbose_name

        models_info.append([reverse('admin:%s_%s_add' %
                                    (model._meta.app_label, model._meta.model_name)),
                         model_name])
    return {'models_info': models_info, }