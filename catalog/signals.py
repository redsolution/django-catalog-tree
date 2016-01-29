from django.db.models import signals
from django.core.cache import cache
from catalog.utils import get_catalog_models
from catalog.models import TreeItem


def insert_in_tree(sender, instance, **kwargs):
    """
    Create TreeItem object after content object created
    """
    created = kwargs.pop('created', False)
    if created:
        tree_item = TreeItem(parent=None, content_object=instance)
        tree_item.save()
        if tree_item.get_slug():
            cache.set(instance.cache_url_key(), instance.full_path())
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