# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse, NoReverseMatch
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
        if self.content_object:
            return unicode(self.content_object)
        else:
            return 'Catalog Tree item'

    def delete(self, *args, **kwargs):
        for child in self.get_children():
            child.delete()
        self.content_object.delete()
        super(TreeItem, self).delete(*args, **kwargs)
    delete.alters_data = True


class CatalogBase(models.Model):
    class Meta:
        abstract = True

    leaf = False
    tree = generic.GenericRelation('TreeItem')
    show = models.BooleanField(verbose_name=_('Show on site'), default=True)

    def get_complete_slug(self):
        try:
            url = self.slug
            if not self.tree.get().is_root():
                for ancestor in self.tree.get().get_ancestors():
                    url = ancestor.content_object.slug + '/' + url
            return url
        except AttributeError:
            pass

    def get_absolute_url(self):
        try:
            return reverse('catalog-item', kwargs={'path': self.get_complete_slug()})
        except NoReverseMatch:
            pass
