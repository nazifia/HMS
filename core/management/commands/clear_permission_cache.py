"""
Management command to clear all UI permission caches.
Useful after making bulk permission changes or troubleshooting cache issues.
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from core.models import UIPermission


class Command(BaseCommand):
    help = 'Clear all UI permission caches'

    def add_arguments(self, parser):
        parser.add_argument(
            '--element-id',
            type=str,
            help='Clear cache for a specific permission element ID only',
        )

    def handle(self, *args, **options):
        element_id = options.get('element_id')

        if element_id:
            # Clear cache for specific permission
            try:
                perm = UIPermission.objects.get(element_id=element_id)
                cleared = perm.clear_cache()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Cleared {cleared} cached entries for permission: {element_id}'
                    )
                )
            except UIPermission.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'✗ Permission not found: {element_id}')
                )
                return

        else:
            # Clear all UI permission caches
            self.stdout.write('Clearing all UI permission caches...')

            try:
                # Try pattern deletion first (faster)
                cache.delete_pattern("ui_perm_*")
                self.stdout.write(
                    self.style.SUCCESS('✓ Cleared all UI permission caches using pattern deletion')
                )
            except AttributeError:
                # Fallback: clear entire cache
                cache.clear()
                self.stdout.write(
                    self.style.WARNING('⚠ Cleared entire cache (pattern deletion not supported by cache backend)')
                )

            self.stdout.write(
                self.style.SUCCESS('✓ Cache clearing complete!')
            )

        # Display current cache info
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Cache Information:')
        self.stdout.write(f'Cache Backend: {cache.__class__.__name__}')

        # Test cache
        test_key = 'cache_test_key'
        cache.set(test_key, 'test_value', 10)
        test_result = cache.get(test_key)

        if test_result == 'test_value':
            self.stdout.write(self.style.SUCCESS('✓ Cache is working properly'))
            cache.delete(test_key)
        else:
            self.stdout.write(self.style.ERROR('✗ Cache may not be working correctly'))

        self.stdout.write('='*60)
