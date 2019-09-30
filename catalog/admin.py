# -*- coding: utf-8 -*-
import json
from django.contrib import admin
from django.contrib.admin.utils import label_for_field
from django.template.response import TemplateResponse
from django.conf.urls import url
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import Promise
from django.utils.encoding import force_text
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models.fields import FieldDoesNotExist
from django.apps import apps
from django.http import JsonResponse, HttpResponse
from django.core.urlresolvers import reverse
from django import forms
from .models import TreeItem
from .utils import get_catalog_models
from .grid import GridRow
from .signals import content_object_parent_changed, content_object_created, content_object_moved


class LazyEncoder(DjangoJSONEncoder):
    """
    Encoder for lazy translation objects
    """
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)
        return super(LazyEncoder, self).default(obj)


class CatalogAdmin(admin.ModelAdmin):
    change_list_template = 'admin/catalog/tree_list.html'
    model = TreeItem

    def changelist_view(self, request):
        if not self.has_change_permission(request, None):
            raise PermissionDenied
        opts = self.model._meta
        app_label = opts.app_label
        title = opts.verbose_name
        app_config = apps.get_app_config(app_label)

        context = {
            'app_label': app_label,
            'title': title,
            'opts': opts,
            'app_config': app_config,
            'site_header': self.admin_site.site_header,
        }
        return TemplateResponse(request, self.change_list_template, context)


    def has_add_permission(self, request):
        """
        Block add permission
        """
        return False

    def get_display_fields(self, models):
        """
        :param models: List of models
        :return: List fields for display. Format [field name, field label]
        """
        fields = []
        field_names = []
        for model_cls in models:
            admin_cls = admin.site._registry[model_cls]
            for field_name in admin_cls.list_display:
                if field_name not in field_names:
                    if field_name == '__str__' or field_name == '__unicode__':
                        field_label = _(u'Object name')
                        fields.insert(0, [field_name, field_label])
                    else:
                        field_label = unicode(label_for_field(field_name,
                                                              model_cls,
                                                              admin_cls))
                        fields.append([field_name, field_label])
                    field_names.append(field_name)
        return fields

    def get_node_data(self, treeitem):
        """
        :param treeitem: TreeItem object
        :return: JSON data of TreeItem object and his content_object
        """
        node = {}
        obj = treeitem.content_object
        if treeitem.parent is None:
            node['parent'] = '#'
        else:
            node['parent'] = treeitem.parent.id
        if obj.leaf is True:
            node['type'] = 'leaf'
        node['id'] = treeitem.id
        node['text'] = treeitem.__unicode__()
        node['data'] = {}
        change_link = reverse('admin:{0}_{1}_change'. \
                              format(obj.__class__._meta.app_label,
                                     obj.__class__.__name__.lower()),
                              args=(obj.id,))
        copy_link = reverse('admin:{0}_{1}_add'. \
                            format(obj.__class__._meta.app_label,
                                   obj.__class__._meta.model_name)) + \
                    '?copy={}'.format(treeitem.id)

        watch_link = reverse('catalog-item', args=(treeitem.content_object.get_complete_slug(),))

        node['data']['change_link'] = change_link
        node['data']['copy_link'] = copy_link
        node['data']['watch_link'] = watch_link

        if obj.leaf is False:
            node['data']['add_links'] = []
            for model_cls in get_catalog_models():
                node['data']['add_links'].\
                    append({
                           'url': reverse('admin:{0}_{1}_add'. \
                                          format(model_cls._meta.app_label,
                                                 model_cls._meta.model_name))
                                  + '?target={}'.format(treeitem.id),
                           'label': _(u'Add %(model_name)s') %
                                    {
                                    'model_name': model_cls._meta.verbose_name
                                    }
                           })
        return node

    def json_tree(self, request):
        """
        :param request:
        :return: JSON structure of catalog for jsTree
        """
        tree = []
        for treeitem in TreeItem.objects.all():
            tree.append(self.get_node_data(treeitem))
        return JsonResponse(tree, safe=False, encoder=LazyEncoder)

    def move_tree_item(self, request):
        """
        Moves node relative to a given target node as specified
        by position
        :param request:
            request.POST contains item_id, target_id, position
            item_id: id of movable node
            target_id: id of target node
            valid values for position are first-child, last-child, left, right
        :return: JSON data with results of operation
        """
        if request.method == "POST":
            position = request.POST.get('position', None)
            target_id = request.POST.get('target_id', None)
            item_id = request.POST.get('item_id', None)

            if item_id and position and target_id:
                try:
                    node = TreeItem.objects.get(id=item_id)
                    target = TreeItem.objects.get(id=target_id)
                except TreeItem.DoesNotExist:
                    message = _(u'Object does not exist')
                    return JsonResponse({'status': 'error',
                                         'type_message': 'error',
                                         'message': message},
                                        encoder=LazyEncoder,)
                slug = node.get_slug()
                if slug is not None and \
                        not TreeItem.check_slug(target, position,
                                                node.get_slug(), node=node):
                    message = _(u'Invalid move. Slug %(slug)s exist in '
                                u'this level') % {'slug': node.get_slug()}
                    return JsonResponse({
                                        'status': 'error',
                                        'type_message': 'error',
                                        'message': message
                                        },
                                        encoder=LazyEncoder)

                parent_from = node.parent.content_object if node.parent else None
                node.move_to(target, position)
                parent_to = node.parent.content_object if node.parent else None

                if parent_from != parent_to:
                    content_object_parent_changed.send(
                        sender=None,
                        instance=node.content_object,
                        parent_from=parent_from,
                        parent_to=parent_to,
                    )

                content_object_moved.send(
                    sender=None,
                    instance=node.content_object,
                    parent_from=parent_from,
                    parent_to=parent_to,
                )

                message = _(u'Successful move')
                return JsonResponse({'status': 'OK', 'type_message': 'info',
                                     'message': message}, encoder=LazyEncoder)
        message = _(u'Bad request')
        return JsonResponse({'status': 'error', 'type_message': 'error',
                             'message': message}, encoder=LazyEncoder)

    def edit_tree_item(self, request):
        """
        Edit Catalog object
        :param request:
            request.body contains fields data
        :return: JSON data with results of operation and errors
        """
        if request.method == 'PUT':
            data = json.loads(request.body.decode('utf-8'))
            try:
                treeitem = TreeItem.objects.get(id=data['id'])
            except TreeItem.DoesNotExist:
                message = _(u'Object does not exist')
                return JsonResponse({'status': 'error',
                                     'type_message': 'error',
                                     'message': message},
                                    encoder=LazyEncoder,)

            obj = treeitem.content_object
            errors = {}
            admin_cls = admin.site._registry[type(obj)]
            for field in data:
                if field in admin_cls.list_display and \
                                field in admin_cls.list_editable:
                    value = data[field]['value']
                    try:
                        modelfield = obj.__class__._meta.get_field(field)
                        setattr(obj, field,
                                modelfield.clean(modelfield.to_python(value),
                                                 obj))
                    except ValidationError:
                        errors[field] = value
                    except FieldDoesNotExist:
                        pass
            if errors:
                message = _(u'Correct the mistakes')
                return JsonResponse({'errors': errors,
                                     'status': 'error',
                                     'type_message': 'error',
                                     'message': message},
                                    encoder=LazyEncoder)
            obj.save()
            message = _(u'Save changes')
            return JsonResponse({'status': 'OK', 'type_message': 'info',
                                 'message': message}, encoder=LazyEncoder)
        else:
            message = _(u'Bad request')
            return JsonResponse({'status': 'error', 'type_message': 'error',
                                 'message': message}, encoder=LazyEncoder)

    def delete_tree_item(self, request):
        """
        Delete TreeItem object
        :param request:
            request.POST contains item_id: if of removed TreeItem object
        :return: JSON data with results of operation
        """
        if request.method == "POST":
            item_id = request.POST.get('item_id', None)
            try:
                treeitem = TreeItem.objects.get(id=item_id)
                treeitem.delete()
                message = _(u'Deleted object')
                return JsonResponse({'status': 'OK', 'type_message': 'info',
                                     'message': message}, encoder=LazyEncoder)
            except TreeItem.DoesNotExist:
                message = _(u'Object does not exist')
                return JsonResponse({'status': 'error',
                                     'type_message': 'error',
                                     'message': message}, encoder=LazyEncoder)
        message = _(u'Bad request')
        return JsonResponse({'status': 'error', 'type_message': 'error',
                             'message': message}, encoder=LazyEncoder)

    def list_children(self, request, parent_id=None):
        """
        :param parent_id: id of parent TreeItem object
        :return: JSON data with fields for display and list children of
        the parent node
        """
        if parent_id is None:
            nodes_qs = TreeItem.objects.root_nodes()
        else:
            nodes_qs = TreeItem.objects.get(id=int(parent_id)).get_children()

        response = {}
        if nodes_qs.count() == 0:
            return JsonResponse(response)
        distinct_node_types = []
        try:
            distinct_node_types = nodes_qs.order_by('content_type__id').distinct('content_type__id')
            distinct_node_types.exists()
        except NotImplementedError:
            # backend sqlite3 not supported DISTINCT operation
            from django.db.models import Min
            distinct_node_types = nodes_qs.order_by('content_type__id').annotate(content_type__id=Min('content_type__id'))

        models = [node.content_object.__class__ for node in distinct_node_types]
        fields = self.get_display_fields(models)
        nodes = []
        for item in nodes_qs:
            admin_cls = admin.site._registry[type(item.content_object)]
            node = GridRow(item.content_object,
                           [field[0] for field in fields], admin_cls)
            nodes.append(node.json_data())

        response['fields'] = fields
        response['nodes'] = nodes

        return JsonResponse(response, safe=False, encoder=LazyEncoder)

    def get_urls(self):
        return [
            url(r'^tree/$', self.admin_site.admin_view(self.json_tree)),
            url(r'^move/$', self.admin_site.admin_view(self.move_tree_item)),
            url(r'^edit/$', self.admin_site.admin_view(self.edit_tree_item)),
            url(r'^delete/$', self.admin_site.admin_view(self.delete_tree_item)),
            url(r'^list_children/(\d+)$', self.admin_site.admin_view(self.list_children)),
            url(r'^list_children/', self.admin_site.admin_view(self.list_children)),
        ] + super(CatalogAdmin, self).get_urls()

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

        FormClass = super(CatalogItemBaseAdmin, self).get_form(request, obj,
                                                               **kwargs)

        class ModelFormCatalogWrapper(FormClass):
            """
            ModelForm wrapper for check slug
            """
            def clean_slug(self):
                """
                :return: slug if objects with this slug do not exist in this
                        level
                        else raise validation error
                """
                slug = self.cleaned_data['slug']
                if obj is None:
                    node = None
                    target = None
                    position = 'last-child'
                else:
                    node = obj.tree.get()
                    target = node
                    position = 'left'
                target_id = request.GET.get('target', None)
                copy_id = request.GET.get('copy', None)
                if target_id or copy_id:
                    try:
                        if target_id:
                            target = TreeItem.objects.get(pk=target_id)
                        elif copy_id:
                            target = TreeItem.objects.get(pk=copy_id).parent
                    except TreeItem.DoesNotExist:
                        pass
                    position = 'last-child'
                if not TreeItem.check_slug(target, position, slug, node):
                    message = _(u'Slug %(slug)s already exist in this '
                                u'level') % {'slug': self.cleaned_data['slug']}
                    raise forms.ValidationError(message)
                return slug

        return ModelFormCatalogWrapper

    def save_model(self, request, obj, form, change):
        """
        Override save_model.
        Moves TreeItem object if request.POST contains target node or
        copied node
        """
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
            if not change:
                # signal sending when obj created only
                parent = target.content_object
                content_object_created.send(
                    sender=None,
                    instance=obj,
                    parent=parent,
                )
        if target and copy_id:
            obj.tree.get().move_to(target.parent, 'last-child')
            # signal sending when obj created only
            parent = target.parent.content_object
            content_object_created.send(
                sender=None,
                instance=obj,
                parent=parent,
            )

    def add_view(self, request, form_url="", extra_context=None):
        """
        Override add_view.
        Fills change form data of copied object
        """
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
                    data[field.name] = getattr(target.content_object,
                                               field.name)
        request.GET = data
        return super(CatalogItemBaseAdmin, self).add_view(request, form_url="",
                                                 extra_context=extra_context)