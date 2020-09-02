# -*- coding: utf-8 -*-
from django.views.generic import DetailView, TemplateView
from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist, FieldError, ImproperlyConfigured
from .models import TreeItem
from .utils import get_catalog_models, get_content_objects, get_sorted_content_objects


class CatalogRootView(TemplateView):
    """
    Render catalog root page
    """
    template_name = 'catalog/root.html'

    def get_context_data(self, **kwargs):
        context = super(CatalogRootView, self).get_context_data(**kwargs)
        # get single root object defining from custom model as CatalogRoot
        root = TreeItem.objects.root_nodes().first()
        root_page = root.content_object if root else None
        object_list = get_sorted_content_objects(get_content_objects(root.get_children())) if root else TreeItem.objects.none()
        context.update({
            'object': root_page,
            'object_list': object_list
        })
        return context


class CatalogItemView(DetailView):
    """
    Render catalog page for object
    """
    def get_template_names(self):
        try:
            names = super(CatalogItemView, self).get_template_names()
        except ImproperlyConfigured:
            names = []
        names.append("catalog/{}.html".format(self.object._meta.model_name))
        return names

    def get_object(self, queryset=None):
        path = self.kwargs.get('path', None)
        if path.endswith('/'):
            path = path[:-1]
        slug = path.split('/')[-1]
        catalog_items = []

        for model_cls in get_catalog_models():
            try:
                item = model_cls.objects.get(slug=slug)
            except (ObjectDoesNotExist, FieldError):
                pass
            else:
                catalog_items.append(item)

        for item in catalog_items:
            try:
                complete_slug = item.get_complete_slug()
            except ObjectDoesNotExist:
                raise Http404
            if complete_slug == path:
                return item

        raise Http404