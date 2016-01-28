from django.db.models import signals
from catalog.utils import get_catalog_models
from catalog.models import TreeItem


def insert_in_tree(sender, instance, **kwargs):

    created = kwargs.pop('created', False)
    if created:
        tree_item = TreeItem(parent=None, content_object=instance)
        tree_item.save()


def delete_content_object(sender, instance, **kwargs):
    for child in instance.get_children():
        child.delete()
    if instance.content_object:
        instance.content_object.delete()

for model_cls in get_catalog_models():
    signals.post_save.connect(insert_in_tree, sender=model_cls)

signals.post_delete.connect(delete_content_object, sender=TreeItem)