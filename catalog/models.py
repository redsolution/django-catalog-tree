# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse, NoReverseMatch
from django.core.cache import cache
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
        """
        Check contains slug attribute in content_object model
        :return: slug or None
        """
        try:
            return self.content_object.slug
        except AttributeError:
            return None

    @classmethod
    def check_slug(self, target, position, slug, node):
        """
        Check unique of `slug` in this level (relative target node by position)
        :return: True if slug is unique or False
        """
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
    TREEITEM_URL_KEY = 'treeitem_%d_url'

    def cache_url_key(self):
        return self.TREEITEM_URL_KEY % self.tree.get().id

    def clear_cache(self):
        cache.delete(self.cache_url_key())

    def full_path(self):
        """
        Get url path ancestors
        """
        try:
            url = self.slug
            if not self.tree.get().is_root_node():
                for ancestor in self.tree.get().get_ancestors(ascending=True):
                    url = ancestor.content_object.slug + '/' + url
            return url
        except AttributeError:
            return None

    def get_complete_slug(self):
        """
        :return: full url of object.
        """
        key = self.cache_url_key()
        url = cache.get(key, None)
        if url is None:
            url = self.full_path()
            if url is not None:
                cache.set(key, url)
        return url

    def get_absolute_url(self):
        path = self.get_complete_slug()
        if path:
            try:
                return reverse('catalog-item', kwargs={'path': path})
            except NoReverseMatch:
                pass
        else:
            return ''
