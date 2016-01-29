# -*- coding: utf-8 -*-
from django import template
from django.template.loader import render_to_string
from classytags.core import Tag, Options
from classytags.arguments import Argument
from catalog.models import TreeItem
from catalog.utils import get_content_objects, get_catalog_models

TREE_TYPE_EXPANDED = 'expanded'
TREE_TYPE_COLLAPSED = 'collapsed'
TREE_TYPE_DRILLDOWN = 'drilldown'

DESCENDANTS_TYPE_ALL = 'all'
DESCENDANTS_TYPE_DIRECT = 'direct'

register = template.Library()


class CatalogChildren(Tag):
    """
    Render or get chlidren for given object.

    Parameters:
        for
            Content object
        type
            Model name
        descendants
            get children or all descendants
        as
            Name of context variable with result.
    """
    name = 'catalog_children'
    template = 'catalog/children_tag.html'

    options = Options(
        'for',
        Argument('instance', required=False),
        'type',
        Argument('model_type', required=False, resolve=False),
        'descendants',
        Argument('descendants', required=False,
                 default=DESCENDANTS_TYPE_DIRECT, resolve=False),
        'as',
        Argument('varname', required=False, resolve=False)
    )

    def render_tag(self, context, instance, model_type, descendants, varname):
        if instance:
            if descendants == DESCENDANTS_TYPE_ALL:
                children = instance.tree.get().get_descendants()
            elif descendants == DESCENDANTS_TYPE_DIRECT:
                children = instance.tree.get().get_children()
        else:
            children = TreeItem.objects.root_nodes()

        if model_type:
            ModelClass = None
            for model_cls in get_catalog_models():
                if model_cls._meta.model_name == model_type:
                    ModelClass = model_cls
            if ModelClass is not None:
                allowed_ids = children.filter(
                    content_type__model=model_type).values_list('object_id',
                                                                flat=True)
                queryset = ModelClass.objects.filter(id__in=allowed_ids).order_by('tree__tree_id', 'tree__lft')
            else:
                queryset = []
        else:
            queryset = get_content_objects(children)
        if varname:
            context[varname] = queryset
            return u''
        else:
            context['children'] = queryset
            return render_to_string(self.template, context)

register.tag(CatalogChildren)


class CatalogTreeRender(Tag):
    """
    Render catalog links for menu or sitemap
    Parameters:
        for
            TreeItem object
        type
            Menu type. Three types available:
            `drilldown` - enabled by default. It will expand only active
                path in tree
            `collapsed` - menu will be collapsed only to dislpay root elements
            `expanded` - all menu nodes will be expanded
        template
            Name template for render tree
    """
    name = 'render_catalog_tree'
    template = 'catalog/tree.html'
    options = Options(
        'for',
        Argument('treeitem', required=False),
        'type',
        Argument('tree_type', required=False, resolve=True,
                 default=TREE_TYPE_DRILLDOWN),
        'template',
        Argument('template', required=False)
    )

    def render_tag(self, context, treeitem, tree_type, template):
        if treeitem:
            tree_list = list(treeitem.get_children())
        else:
            tree_list = list(TreeItem.objects.root_nodes())

        context['tree_list'] = get_content_objects(tree_list)
        context['type'] = tree_type

        if template:
            output = render_to_string(template, context)
        else:
            output = render_to_string(self.template, context)
        return output

register.tag(CatalogTreeRender)


@register.inclusion_tag('catalog/breadcrumbs.html', takes_context=True)
def catalog_breadcrumbs(context, instance):
    """
    Get breadcrumbs for catalog object
    """
    treeitem = instance.tree.get()
    context.update({'breadcrumbs':
                        get_content_objects(treeitem.get_ancestors())})
    return context