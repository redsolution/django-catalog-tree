from django.db.models import signals
from django.core.cache import cache
from .utils import get_catalog_models
from .models import TreeItem
from django.dispatch import Signal

# special signals for situations where standard signals not working correctly
content_object_parent_changed = Signal(providing_args=["instance", "parent_from", "parent_to"])
content_object_moved = Signal(providing_args=["instance", "parent_from", "parent_to"])
content_object_created = Signal(providing_args=["instance", "parent"])


def insert_in_tree(sender, instance, **kwargs):
    """
    Create TreeItem object after content object created
    """
    created = kwargs.pop('created', False)
    if created:
        tree_item = TreeItem(parent=None, content_object=instance)
        tree_item.save()
    else:
        tree_item = instance.tree.get()
        if tree_item.get_slug() and \
                        instance.full_path() != cache.get(instance.cache_url_key()):
            instance.clear_cache()


def delete_content_object(sender, instance, **kwargs):
    """
    Delete children nodes and content object after TreeItem deleted
    """
    for child in instance.get_children():
        child.delete()
    if instance.content_object:
        instance.content_object.delete()

for model_cls in get_catalog_models():
    signals.post_save.connect(insert_in_tree, sender=model_cls)

signals.post_delete.connect(delete_content_object, sender=TreeItem)