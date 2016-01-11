# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _
from django.db import models
from mptt.models import MPTTModel


class TreeItem(MPTTModel):
    class Meta:
        verbose_name = _('Catalog tree item')
        verbose_name_plural = _('Catalog tree')
        ordering = ['tree_id', 'lft']

    parent = models.ForeignKey('self', related_name=_('children'),
                               verbose_name=_('Parent node'), null=True,
                               blank=True, editable=False)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    def __unicode__(self):
        return 'TreeItem - ' + unicode(self.content_object)

    def delete(self, *args, **kwargs):
        for child in self.get_children():
            child.delete()
        self.content_object.delete()
        super(TreeItem, self).delete(*args, **kwargs)
    delete.alters_data = True


class CatalogBase(models.Model):
    class Meta:
        abstract = True

    leaf  = False
    tree = generic.GenericRelation('TreeItem')