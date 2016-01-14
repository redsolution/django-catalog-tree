from django.apps import apps as django_apps
from django.conf import settings


def get_catalog_models():
    for model_path in settings.CATALOG_MODELS:
        app_label, model_name = tuple(model_path.split('.'))
        yield django_apps.get_model(app_label, model_name)


def get_content_objects(catalog_tree_items, show=True):
    if show:
        return [
            item.content_object
            for item in catalog_tree_items if item.content_object.show
        ]
    return [item.content_object for item in catalog_tree_items]