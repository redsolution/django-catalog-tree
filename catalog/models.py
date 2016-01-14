# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.translation import ugettext_lazy as _
from django.db import IntegrityError
from django.db import models
from mptt.models import MPTTModel


class TreeItem(MPTTModel):
    class Meta:
        verbose_name = _('Catalog tree item')
        verbose_name_plural = _('Catalog tree')
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

    def clone(self):
        data_fields = {}
        for field in self._meta.fields:
            if field.name != 'id':
                data_fields[field.name] = getattr(self, field.name)
                if field.name == 'slug':
                    copy_slug = data_fields[field.name] + '-copy'
                    incorrect_slug = True
                    while incorrect_slug:
                        dublicate_slug = False
                        for sibling in self.tree.get().get_siblings():
                            if sibling.get_slug() == copy_slug:
                                copy_slug += '-copy'
                                dublicate_slug = True
                                break
                        if not dublicate_slug:
                            incorrect_slug = False

                    data_fields[field.name] = copy_slug
                if field.name == 'name':
                    data_fields[field.name] += unicode(_('-copy'))
            if field.name != 'slug' and field.name != 'id' and field.unique:
                return None
        while True:
            try:
                clone = self.__class__.objects.create(**data_fields)
                return clone
            except IntegrityError:
                data_fields['slug'] += '-copy'


