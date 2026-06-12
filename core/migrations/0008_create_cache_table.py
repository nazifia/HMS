from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    """Create the database cache table(s) defined in CACHES.

    Production defaults to DatabaseCache (LOCATION 'cache_table'), and the
    session engine is ``cached_db`` — so a missing cache table breaks session
    load/save and silently logs users straight back out. ``createcachetable``
    is idempotent and a no-op for non-database cache backends (e.g. LocMemCache
    in development), so this runs safely in every environment.
    """
    call_command("createcachetable", verbosity=0)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_delete_activitylog"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop),
    ]
