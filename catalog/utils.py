from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from .models import TreeItem


def get_catalog_models():
    """
    Generator for list of registered models in catalog
    """
    for model_path in settings.CATALOG_MODELS:
        app_label, model_name = tuple(model_path.split('.'))
        yield django_apps.get_model(app_label, model_name)


def get_content_objects(catalog_tree_items, show=True, allowed_models=[]):
    """
    :param catalog_tree_items: QuerySet or list of TreeItem objects
    :return: list of content objects
    """
    res = []
    if show:
        for item in catalog_tree_items:
            if hasattr(item.content_object, 'show') and item.content_object.show:
                if allowed_models:
                    if isinstance(item.content_object, allowed_models):
                        res.append(item.content_object)
                else:
                    res.append(item.content_object)
    else:
        for item in catalog_tree_items:
            if allowed_models:
                if isinstance(item.content_object, allowed_models):
                    res.append(item.content_object)
            else:
                res.append(item.content_object)
    return res


def get_sorted_content_objects(content_objects):
    """
    :param content_objects: QuerySet or list of content objects
    :return: list of content objects sorted in tree order
    """
    objects = {}
    for instance in content_objects:
        content_type = ContentType.objects.get_for_model(instance.__class__)
        objects[(content_type.id, instance.id)] = instance
    if not objects:
        return []
    q = Q()
    for content_type, object_id in objects:
        q |= Q(content_type=content_type, object_id=object_id)
    items = TreeItem.objects.filter(q)
    values = items.values_list('content_type', 'object_id')
    return [objects[value] for value in values]