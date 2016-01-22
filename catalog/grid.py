# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db.models.fields import FieldDoesNotExist
from django.utils.html import conditional_escape
from django.db import models


class GridRow(object):

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

            value = ''
            modelfield = None
            if field_name in self.admin_cls.list_display:
                try:
                    modelfield, attr, val = \
                        admin.utils.lookup_field(field_name, self.obj,
                                                 self.admin_cls)
                    value = conditional_escape(admin.utils.display_for_field(val, modelfield))
                except AttributeError:
                    pass


            field_type = 'text'
            correct_values = None
            if modelfield:
                if isinstance(modelfield, models.BooleanField):
                    field_type = 'checkbox'
                    if val:
                        value = 't'
                    else:
                        value = 'f'
                if isinstance(modelfield,
                              (models.IntegerField, models.CharField)) \
                        and modelfield.choices:
                    field_type = 'select'
                    value = val
                    correct_values = dict(modelfield.choices)

            data[field_name] = {
                'type': field_type,
                'value': value,
                'editable': editable,
                'correct_values': correct_values if correct_values else ''
            }
        return data