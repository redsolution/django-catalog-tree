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

    def get_slug(self):
        try:
            return self.content_object.slug
        except AttributeError:
            return None


class CatalogBase(models.Model):
    class Meta:
        abstract = True

    leaf = False
    tree = generic.GenericRelation('TreeItem')
    show = models.BooleanField(verbose_name=_('Show on site'), default=True)

    def get_complete_slug(self):
        try:
            url = self.slug
            if not self.tree.get().is_root_node():
                for ancestor in self.tree.get().get_ancestors(ascending=True):
                    url = ancestor.content_object.slug + '/' + url
            return url
        except AttributeError:
            return None

    def get_absolute_url(self):
        path = self.get_complete_slug()
        if path:
            try:
                return reverse('catalog-item', kwargs={'path': path})
            except NoReverseMatch:
                pass
        else:
            return ''

