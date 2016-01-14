# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.translation import ugettext_lazy as _
from django.db import models
from mptt.models import MPTTModel


class TreeItem(MPTTModel):
    class Meta:
        verbose_name = _('Catalog structure')
        verbose_name_plural = _('Catalog structure')
        ordering = ['tree_id', 'lft']

    parent = models.ForeignKey('self', related_name='children',
                               verbose_name=_('Parent node'), null=True,
                               blank=True, editable=False)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    def __unicode__(self):
        if self.content_object:
            return unicode(self.content_object)
        else:
            return _(u'Catalog Tree item')

    def get_slug(self):
        try:
            return self.content_object.slug
        except AttributeError:
            return None

    @classmethod
    def check_slug(self, target, position, slug, node=None):
        if target is None:
            siblings = TreeItem.objects.root_nodes()
        else:
            if position == 'first-child' or position == 'last-child':
                siblings = target.get_children()
            else:
                siblings = target.get_siblings(include_self=True)
        for sibling in siblings:
            if sibling != node and \
               sibling.get_slug() == slug:
                return False
        return True


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

