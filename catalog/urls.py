# -*- coding: utf-8 -*-
from django.conf.urls import url
from .views import CatalogRootView, CatalogItemView

urlpatterns = [
    url(r'^$', CatalogRootView.as_view(), name='catalog-root'),
    url(r'^(?P<path>.*)/$', CatalogItemView.as_view(), name='catalog-item'),
]