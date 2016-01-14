# -*- coding: utf-8 -*-
from django.contrib import admin
from django.template.response import TemplateResponse
from django.conf.urls import patterns, url
from django.utils.translation import ugettext_lazy as _
from django.utils.html import strip_tags
from django.utils.functional import Promise
from django.utils.encoding import force_text
from django.core.serializers.json import DjangoJSONEncoder
from django.apps import apps
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.urlresolvers import reverse
from django import forms
from catalog.models import TreeItem
from catalog.utils import get_catalog_models


class LazyEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)
        return super(LazyEncoder, self).default(obj)


class CatalogAdmin(admin.ModelAdmin):
    change_list_template = 'admin/catalog/tree_list.html'
    model = TreeItem

    def changelist_view(self, request):
        opts = self.model._meta
        app_label = opts.app_label
        title = opts.verbose_name
        app_config = apps.get_app_config(app_label)

        context = {
            'app_label': app_label,
            'title': title,
            'opts': opts,
            'app_config': app_config,
        }
        return TemplateResponse(request, self.change_list_template,
                                context, current_app=self.admin_site.name)

    def get_node_data(self, treeitem):
        node = {}
        if treeitem.parent is None:
            node['parent'] = '#'
        else:
            node['parent'] = treeitem.parent.id
        if treeitem.content_object.leaf is True:
            node['type'] = 'leaf'
        node['id'] = treeitem.id
        node['text'] = treeitem.__unicode__()
        node['data'] = {}
        node['data']['change_link'] = reverse('admin:{0}_{1}_change'.
                                              format(treeitem.content_object.__class__._meta.app_label,
                                                     treeitem.content_object.__class__.__name__.lower()),
                                              args=(treeitem.content_object.id,))
        node['data']['copy_link'] = reverse('admin:{0}_{1}_add'.
                                            format(treeitem.content_object.__class__._meta.app_label,
                                                   treeitem.content_object.__class__._meta.model_name)) + \
                                    '?copy={}'.format(treeitem.id)
        if treeitem.content_object.leaf is False:
            node['data']['add_links'] = []
            for model_cls in get_catalog_models():
                node['data']['add_links'].\
                    append({'url': reverse('admin:{0}_{1}_add'.format(model_cls._meta.app_label,
                                                                      model_cls._meta.model_name)) + '?target={}'.
                    format(treeitem.id), 'label': _(u'Add %(model_name)s') % {'model_name': model_cls._meta.verbose_name}})
        return node

    def json_tree(self, request):
        tree = []
        for treeitem in TreeItem.objects.all():
            tree.append(self.get_node_data(treeitem))
        return JsonResponse(tree, safe=False, encoder=LazyEncoder)

    def move_tree_item(self, request, item_id):
        position = request.GET.get('position', None)
        target_id = request.GET.get('target_id', None)

        if position and target_id:
            node = get_object_or_404(TreeItem, id=item_id)
            target = get_object_or_404(TreeItem, id=target_id)
            if position != 'first-child':
                for sibling in target.get_siblings(include_self=True):
                    if sibling != node and sibling.get_slug() == node.get_slug() and node.get_slug() is not None:
                        message = _(u'Invalid move. Slug %(slug)s exist in this level') % {'slug': sibling.get_slug()}
                        return JsonResponse({'status': 'error', 'type_message': 'error', 'message': message},
                                            encoder=LazyEncoder)
            node.move_to(target, position)
        message = _(u'Successful move')
        return JsonResponse({'status': 'OK', 'type_message': 'info', 'message': message}, encoder=LazyEncoder)

    def delete_tree_item(self, request, item_id):
        if item_id:
            try:
                treeitem = TreeItem.objects.get(id=item_id)
                treeitem.delete()
                message = _(u'Deleted object %(object_name)s') % {'object_name': treeitem.__unicode__()}
                return JsonResponse({'status': 'OK', 'type_message': 'info', 'message': message}, encoder=LazyEncoder)
            except TreeItem.DoesNotExist:
                message = _(u'Object does not exist')
                return JsonResponse({'status': 'error', 'type_message': 'error', 'message': message},
                                    encoder=LazyEncoder)

    def list_children(self, request, parent_id=None):

        if parent_id is None:
            nodes_qs = TreeItem.objects.root_nodes()
        else:
            nodes_qs = TreeItem.objects.get(id=int(parent_id)).get_children()

        response = {}
        if nodes_qs.count() == 0:
            return JsonResponse(response)

        fields = []
        field_names = []
        for model_cls in get_catalog_models():
            admin_cls = admin.site._registry[model_cls]
            for field_name in admin_cls.list_display:
                if field_name not in field_names and field_name != '__str__':
                    field_label = unicode(admin.utils.label_for_field(field_name, model_cls, admin_cls))
                    fields.append([field_name, field_label])
                    field_names.append(field_name)

        nodes = []
        for item in nodes_qs:
            node = {}
            item_dict = item.content_object.__dict__
            for field in fields:
                try:
                    field_content = item_dict[field[0]]
                    if isinstance(field_content, (unicode, str)):
                        field_content = strip_tags(field_content[:200])
                    node[field[0]] = field_content
                except KeyError:
                    node[field[0]] = ''
            nodes.append(node)

        response['fields'] = fields
        response['nodes'] = nodes

        return JsonResponse(response, safe=False)

    def get_urls(self):
        return patterns('',
            url(r'^tree/$', self.admin_site.admin_view(self.json_tree)),
            url(r'^move/(\d+)$', self.admin_site.admin_view(self.move_tree_item)),
            url(r'^delete/(\d+)$', self.admin_site.admin_view(self.delete_tree_item)),
            url(r'^copy/(\d+)$', self.admin_site.admin_view(self.copy_tree_item)),
            url(r'^list_children/(\d+)$', self.admin_site.admin_view(self.list_children)),
            url(r'^list_children/', self.admin_site.admin_view(self.list_children)),
        ) + super(CatalogAdmin, self).get_urls()

admin.site.register(TreeItem, CatalogAdmin)


class CatalogItemBaseAdmin(admin.ModelAdmin):

    def response_change(self, request, obj):

        if '_popup' in request.POST:
            return HttpResponse('''
               <script type="text/javascript">
                  opener.dismissAddAnotherPopup(window);
               </script>''')
        return super(CatalogItemBaseAdmin, self).response_change(request, obj)

    def get_form(self, request, obj=None, **kwargs):

        FormClass = super(CatalogItemBaseAdmin, self).get_form(request, obj, **kwargs)

        class ModelFormCatalogWrapper(FormClass):

            def clean_slug(self):
                slug = self.cleaned_data['slug']
                if obj is None:
                    siblings = TreeItem.objects.root_nodes()
                else:
                    siblings = obj.tree.get().get_siblings()
                target_id = request.GET.get('target', None)
                if target_id:
                    try:
                        target = TreeItem.objects.get(pk=target_id)
                        siblings = target.get_children()
                    except TreeItem.DoesNotExist:
                        pass
                for sibling in siblings:
                    if sibling.get_slug() == self.cleaned_data['slug']:
                        raise forms.ValidationError(_(u'Slug %(slug)s already exist in this level') %
                                                    {'slug': self.cleaned_data['slug']})
                return slug

        return ModelFormCatalogWrapper

    def save_model(self, request, obj, form, change):
        target_id = request.GET.get('target', None)
        copy_id = request.GET.get('copy', None)
        target = None
        if target_id or copy_id:
            try:
                if target_id:
                    target = TreeItem.objects.get(pk=target_id)
                elif copy_id:
                    target = TreeItem.objects.get(pk=copy_id)
            except TreeItem.DoesNotExist:
                pass
        obj.save()
        if target and target_id:
            obj.tree.get().move_to(target, 'last-child')
        if target and copy_id:
            obj.tree.get().move_to(target.parent, 'last-child')

    def add_view(self, request, form_url="", extra_context=None):
        data = request.GET.copy()
        target_id = request.GET.get('copy', None)
        target = None
        if target_id:
            try:
                target = TreeItem.objects.get(pk=target_id)
            except TreeItem.DoesNotExist:
                pass
        if target:
            for field in target.content_object._meta.fields:
                if field.name != 'id':
                    data[field.name] = getattr(target.content_object, field.name)
        request.GET = data
        return super(CatalogItemBaseAdmin, self).add_view(request, form_url="",
                                                 extra_context=extra_context)