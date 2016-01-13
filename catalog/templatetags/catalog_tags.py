# -*- coding: utf-8 -*-
from django import template
from django.template.loader import render_to_string
from classytags.core import Tag, Options
from classytags.arguments import Argument
from catalog.models import TreeItem
from catalog.utils import get_content_objects

register = template.Library()


class CatalogChildren(Tag):
    name = 'catalog_children'
    template = 'catalog/children_tag.html'

    options = Options(
        'for',
        Argument('instance', required=False),
        'type',
        Argument('model_type', required=False, resolve=False),
        'as',
        Argument('varname', required=False, resolve=False)
    )

    def render_tag(self, context, instance, model_type, varname):
        if instance:
            children = instance.tree.get().get_children()
            if model_type:
                children = children.filter(content_type__model=model_type)
        else:
            children = TreeItem.objects.root_nodes()
            if model_type:
                children = children.filter(content_type__model=model_type)

        if varname:
            context[varname] = get_content_objects(children)
            return u''
        else:
            context['children'] = get_content_objects(children)
            return render_to_string(self.template, context)

register.tag(CatalogChildren)


class CatalogTreeRender(Tag):
    """
    Render catalog links for menu or sitemap
    """
    name = 'render_catalog_tree'
    template = 'catalog/tree.html'
    options = Options(
        'for',
        Argument('treeitem', required=False),
        'template',
        Argument('template', required=False)
    )

    def render_tag(self, context, treeitem, template):
        if treeitem:
            tree_list = list(treeitem.get_children())
        else:
            tree_list = list(TreeItem.objects.root_nodes())

        context['tree_list'] = get_content_objects(tree_list)

        if template:
            output = render_to_string(template, context)
        else:
            output = render_to_string(self.template, context)
        return output

register.tag(CatalogTreeRender)


@register.inclusion_tag('catalog/breadcrumbs.html', takes_context=True)
def catalog_breadcrumbs(context, instance):
    context.update({'breadcrumbs': get_content_objects(instance.tree.get().get_ancestors())})
    return context