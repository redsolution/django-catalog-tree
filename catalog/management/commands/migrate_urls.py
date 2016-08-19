from optparse import make_option
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.contrib.redirects.models import Redirect
from catalog.models import TreeItem


class Command(BaseCommand):
    help = ('Create redirects for old catalog urls (/catalog_prefix/model/slug/).')

    option_list = BaseCommand.option_list + (
        make_option('-p', '--prefix', action='store', type='string', dest='url_prefix',
                    help='Url conf prefix for old catalog urls. default: catalog'),
    )
    can_import_settings = True

    def handle(self, *args, **options):
        items = TreeItem.objects.all()
        url_prefix = options.get('url_prefix') if options.get('url_prefix') else 'catalog'

        with transaction.atomic():
            for item in items:
                content_object = item.content_object
                if content_object:
                    old_url = '/{}/{}/{}/'.format(
                        url_prefix,
                        content_object.__class__.__name__,
                        content_object.slug
                    ).lower()
                    redirect, create= Redirect.objects.get_or_create(
                        old_path=old_url,
                        site_id=settings.SITE_ID
                    )
                    redirect.new_path = content_object.get_absolute_url()
                    redirect.save()
