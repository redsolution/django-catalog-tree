from django.contrib import admin
from django.template.response import TemplateResponse
from django.conf.urls import patterns, url
from django.apps import apps
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from catalog.models import TreeItem
from catalog.utils import get_catalog_models


class CatalogAdmin(admin.ModelAdmin):
    change_list_template = u'catalog/admin/tree_list.html'
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
            'app_config': app_config
        }
        return TemplateResponse(request, self.change_list_template,
                                context, current_app=self.admin_site.name)

    def json_tree(self, request):
        tree = []
        for node in TreeItem.objects.all():
            a = {}
            if node.parent is None:
                a['parent'] = '#'
            else:
                a['parent'] = node.parent.id
            if node.content_object.leaf is True:
                a['type'] = 'leaf'
            a['id'] = node.id
            a['text'] = node.content_object.__unicode__()
            tree.append(a)
        return JsonResponse(tree, safe=False)

    def move_tree_item(self, request, item_id):
        position = request.GET.get('position', None)
        target_id = request.GET.get('target_id', None)
        print position, target_id

        if position and target_id:
            tree = get_object_or_404(TreeItem, id=item_id)
            target = get_object_or_404(TreeItem, id=target_id)
            tree.move_to(target, position)
        return HttpResponse()

    def delete_tree_item(self, request, item_id):
        if(item_id):
            tree = get_object_or_404(TreeItem, id=item_id)
            tree.delete()
            return HttpResponse()

    def list_children(self, request, parent_id=None):

        if parent_id is None:
            nodes_qs = TreeItem.objects.root_nodes()
        else:
            nodes_qs = TreeItem.objects.get(id=int(parent_id)).get_children()

        response = {}
        if nodes_qs.count() == 0:
            return JsonResponse(response)

        fields = []
        for model_cls in get_catalog_models():
            model_fields = model_cls._meta.get_all_field_names()
            model_fields.remove('tree')
            fields += model_fields

        fields = set(fields)
        fields = list(fields)

        nodes = []
        for item in nodes_qs:
            node = {}
            item_dict = item.content_object.__dict__
            for field in fields:
                try:
                    node[field] = item_dict[field]
                except KeyError:
                    node[field] = ''
            nodes.append(node)

        response['fields'] = fields
        response['nodes'] = nodes

        return JsonResponse(response, safe=False)

    def get_urls(self):
        return patterns('',
            url(r'^tree/$', self.admin_site.admin_view(self.json_tree)),
            url(r'^move/(\d+)$', self.admin_site.admin_view(self.move_tree_item)),
            url(r'^delete/(\d+)$', self.admin_site.admin_view(self.delete_tree_item)),
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