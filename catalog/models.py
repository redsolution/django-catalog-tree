# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.urlresolvers import reverse, NoReverseMatch
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from django.db import models
from mptt.models import MPTTModel

try:
    from tinymce.models import HTMLField
except ImportError:
    from django.db.models.fields import TextField as HTMLField


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
    content_object = GenericForeignKey()

    def __unicode__(self):
        if self.content_object:
            return unicode(self.content_object)
        else:
            return unicode(_('Catalog Tree item'))

    def move_to(self, target, position='first-child'):
        """
        Clear cache when moving
        """
        self.content_object.clear_cache()
        super(TreeItem, self).move_to(target, position=position)

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
    tree = GenericRelation(TreeItem)
    show = models.BooleanField(verbose_name=_('Show on site'), default=True)
    last_modified = models.DateTimeField(verbose_name=_('Datetime last modified'), auto_now=True)
    slug = models.SlugField(
        verbose_name=_('Slug'), max_length=255, unique=True,
        help_text=_('The slug will be used to create the page URL, it must be unique among the other pages of the same level.')
    )

    FULL_URL_KEY = '%s_%d_url'


    def cache_url_key(self):
        return self.FULL_URL_KEY % (self.__class__.__name__, self.id)

    def clear_cache(self):
        cache.delete(self.cache_url_key())
        for child in self.tree.get().get_children():
            child.content_object.clear_cache()

    def full_path(self):
        """
        Get url path ancestors
        """
        path = []
        for ancestor in self.tree.get().get_ancestors(ascending=True):
            if ancestor.content_object.slug:
                path.append(ancestor.content_object.slug)
        if self.slug:
            path.append(self.slug)
        return '/'.join(path)

    def get_complete_slug(self):
        """
        :return: full url of object.
        """
        key = self.cache_url_key()
        url = cache.get(key, None)
        if url is None:
            url = self.full_path()
            if url is not None:
                cache.set(key, url, None)
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
