# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db.models.fields import FieldDoesNotExist
from django.utils.html import strip_tags
from django.utils.encoding import smart_unicode


class GridRow(object):

    types = {
        int: 'text',
        unicode: 'text',
        str: 'text',
        bool: 'checkbox'
    }

    EDITABLE_FIELDS = [
        'CharField',
        'IntegerField',
        'PositiveIntegerField',
        'BooleanField'
    ]

    def __init__(self, obj, fields, admin_cls):
        self.obj = obj
        self.fields = fields
        self.admin_cls = admin_cls

    def json_data(self):

        data = {'id': self.obj.tree.get().id}
        for field_name in self.fields:
            editable = True
            try:
                field = self.obj._meta.get_field(field_name)
                if field.get_internal_type() not in self.EDITABLE_FIELDS or \
                        field_name not in self.admin_cls.list_editable:
                        editable = False
            except FieldDoesNotExist:
                editable = False
            try:
                value = admin.utils.lookup_field(field_name, self.obj,
                                                 self.admin_cls)[2]
            except AttributeError:
                value = ''

            field_type = type(value)
            if isinstance(value, (unicode, str)):
                value = strip_tags(value)
                if len(value) > 100:
                    value = value[:100]
                    editable = False

            if field_type == bool:
                if value:
                    value = 't'
                else:
                    value = 'f'

            data[field_name] = {
                'type': self.types[field_type] if field_type in self.types else 'text',
                'value': smart_unicode(value, strings_only=True),
                'editable': editable
            }
        return data