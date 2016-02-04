from django.core.management.base import BaseCommand
from catalog.models import TreeItem
import sys


class Command(BaseCommand):
    help = ('Delete all cache of catalog models')

    def handle(self, *args, **options):
        for item in TreeItem.objects.root_nodes():
            item.content_object.clear_cache()
        sys.stdout.write("\rCache deleted\n")