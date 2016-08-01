from django.conf import settings


CATALOG_BLOCK_ADD_PERMISSION = getattr(
    settings,
    'CATALOG_BLOCK_ADD_PERMISSION',
    True
)