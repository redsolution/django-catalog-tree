# Django catalog tree

Open source catalog management system based on the Django framework and django-mptt library.

## Requirements
- Django 1.11
- Python 2.7
- django-classy-tags >=0.3 and <=0.9.0
- django-mptt 0.9.*

## Installation and basic usage

1. Install package

    ``pip install git+git://github.com/oldroute/django-catalog-tree``

2. Create application for your custom catalog models, for example ``custom_catalog``

    **models.py**

    ```python
    from django.db import models
    from catalog.models import CatalogBase
    ...



    class Root(CatalogBase):
        title = models.CharField(max_length=400)

        def get_absolute_url(self):
            return reverse('catalog-root')

        def __str__(self, *args, **kwargs):
            return self.title


    class Section(CatalogBase):
        title = models.CharField(max_length=400)

        def __str__(self):
            return self.title


    class Product(CatalogBase):
        leaf = True # cannot have children
        title = models.CharField(max_length=400)

        def __str__(self):
            return self.title


    class Category(CatalogBase):
        leaf = True # cannot have children
        title = models.CharField(max_length=400)
        items = models.ManyToManyField(Item, blank=True, null=True, related_name='categories')

        def __str__(self):
            return self.title

    ```

    This is example of simple catalog structure based on four typical models:

    - ``Root`` - represent catalog root page
    - ``Section`` - model for grouping products based on inheritance
    - ``Product`` - endpoint of catalog tree - represent product page
    - ``Category``- special model for grouping products from any section by common attribute

    **admin.py**

    ```python
    from django.contrib import admin
    from catalog.admin import CatalogItemBaseAdmin
    from .models import Root, Section, Product, Category
    ...


    @admin.register(Root)
    class RootAdmin(CatalogItemBaseAdmin):
        model = Root

        def has_add_permission(self, request):
            return not bool(Root.objects.exists())

        def has_delete_permission(self, request, obj=None):
            return False


    @admin.register(Product)
    class ProductAdmin(CatalogItemBaseAdmin):
        model = Product


    @admin.register(Section)
    class SectionAdmin(CatalogItemBaseAdmin):
        model = Section


    @admin.register(Category)
    class CategoryAdmin(CatalogItemBaseAdmin):
        model = Category
    ```
    Create other app files like ``apps.py``. Application setup details are not relevant to this guide.

3. Configure your setting file:

    ``CATALOG_MODELS`` - list of models that will be available for creation in the admin catalog interface. Simple example of configuration:

    ```python
    INSTALLED_APPS += ['catalog', '<PROJECT_ROOT>.custom_catalog']

    CATALOG_MODELS = [
        'custom_catalog.Section',
        'custom_catalog.Product',
        'custom_catalog.Category',
    ]
    ```

5. Add urlpattern to main urls.py:

    ```python
    urlpatterns = [
        ...
        url(r'^catalog/', include('catalog.urls')),
        ...
    ]
    ```

5. Create templates

    For each catalog model your need to create template. Follow next templates structure:

    - catalog/
        - breadcrumbs.html (default template exist)
        - children_tag.html (default template exist)
        - product.html
        - root.html
        - section.html
        - category.html

     The object instance is accessible in the template through the variable ``object`` or by model name. Consider how to work with data in a templates:

    **catalog/base.html**
    ```html
    {% load catalog_tags %}
    ...
    <h1>{{ object.title }}</h1>

    <div class='breadcrumbs'>
        {% block breadcrumbs %}
            {{ block.super }}
            {% catalog_breadcrumbs object %}
        {% endblock %}
    </div>

    {% block content %}{% endblock %}
    ```
    In this examle  ``{% catalog_breadcrumbs object %}`` include rendered catalog bredcrumbs for object (for customize see template ``breadcrumbs.html``). For example: *Catalog-> Section-> Product*

    **catalog/section.html**

    ```html
    {% extends 'catalog/base.html' %}
    {% load catalog_tags %}

    {% block content %}
        <div class='products'>
            <!-- Show products here -->
        </div>
    {% endblock %}
    ```
   In this example we need display  products of current section. Consider ways to display a list of products

   ``{% catalog_children for object %}`` - render ``children_tag.html`` with section all children.

   ``{% catalog_children for object type product %}`` - render ``children_tag.html`` with section **products-children**.

   ``{% catalog_children for object type product descendants all %}`` - render ``children_tag.html`` with section **products-descendants**.

   ``{% catalog_children for object type product descendants all as descendants %}`` - get section **product-descendants** as varible ``descendants``

6. Apply migrations and run local server

    ```python
    python manage.py migrate
    python manage.py runserver
    ```

7. Create catalog root and some catalog items in admin catalog app.

**Configure is done!**

## Advansed usage
#### About requests by catalog tree

All catalog items consist of two records:
- **content_object** - is instance of your custom models (like Product, Section) with represent custom fields.
- **tree** - node to represent postion in catalog structure.

Example №1. Get section tree node: ``section.tree.get()``

Example №2. Get section children tree nodes ``section.tree.get().get_children()`` - QuerySet in result

Example №3. Get section children products

```python
from catalog.utils import get_content_objects
products = get_content_objects(section.tree.get().get_children()) # list in result
```
Example №4. Get section children products sorted by catalog tree structure

```python
from catalog.utils import get_content_objects, get_sorted_content_objects
sorted_products = get_sorted_content_objects(get_content_objects(section.tree.get().get_children()))
```
See other tree methods in [django-mptt docs](https://django-mptt.github.io/django-mptt/models.html)

#### Available catalog events:
If your need to control catalog states you may handle following signals
- **content_object_moved** - fired for content_object when tree node moved. Signal provides next kwargs:
    - instance - content_object
    - parent_from - old parent content_object (moved from)
    - parent_to - new parent content_object (moved to)
- **content_object_parent_changed** - fired for content_object when tree node moved by tree and
when old and new parent do not match. Provides the same kwargs.
- **content_object_created** - fired for content_object when a new record is created. Provides next kwargs:
    - instance - content_object
    - parent - parent content_object (None for root nodes)
- **node_moved** - fired for tree node when it moved by tree. Provide next kwargs:
    - instance - tree node
    - target - new parent tree node (moved to)
    - position - one of predefined values, see django-mptt [docs](https://django-mptt.github.io/django-mptt/mptt.forms.html?highlight=position#mptt.forms.TreeNodePositionField)

Use case example:

**signals.py**
```python
from mptt.signals import node_moved
from catalog.models import TreeItem
from catalog.signals import content_object_parent_changed, content_object_created
from <PROJECT_ROOT>.custom_catalog.models import Product

def handler(sender, instance, **kwargs):
    # for every signal **kwargs contain their provides kwargs
    # for example parent_from = kwargs.get("parent_from")
    # Do something

node_moved.connect(handler, sender=TreeItem)
content_object_created(handler)
content_object_parent_changed.connect(handler)
content_object_moved(handler)
```

