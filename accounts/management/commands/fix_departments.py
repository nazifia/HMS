from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from accounts.models import Department


class Command(BaseCommand):
    help = 'Detect and merge duplicate departments (same hospital + name).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report duplicates without merging anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # A duplicate is more than one Department row sharing the same
        # (hospital, name). This covers tenant-less (hospital IS NULL) rows,
        # which the DB unique_together does not guard because SQL treats NULL
        # as distinct.
        dupe_keys = (
            Department.objects
            .values('hospital', 'name')
            .annotate(c=Count('id'))
            .filter(c__gt=1)
        )

        if not dupe_keys:
            self.stdout.write(self.style.SUCCESS('No duplicate departments found.'))
            return

        total_removed = 0
        for key in dupe_keys:
            rows = list(
                Department.objects
                .filter(hospital=key['hospital'], name=key['name'])
                .order_by('id')
            )
            survivor, doomed = rows[0], rows[1:]
            self.stdout.write(
                f"Duplicate '{key['name']}' (hospital={key['hospital']}): "
                f"keep id={survivor.id}, merge {[d.id for d in doomed]}"
            )

            if dry_run:
                total_removed += len(doomed)
                continue

            with transaction.atomic():
                self._repoint_references(survivor, doomed)
                for d in doomed:
                    d.delete()
                total_removed += len(doomed)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'Dry run: would remove {total_removed} duplicate department(s).'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Merged and removed {total_removed} duplicate department(s).'
            ))

    def _repoint_references(self, survivor, doomed):
        """Move every FK / one-to-one / M2M reference off the doomed rows onto
        the survivor before they are deleted."""
        for rel in Department._meta.related_objects:
            field = rel.field
            related_model = rel.related_model

            if rel.many_to_many:
                through = field.remote_field.through
                dept_col = next(
                    f.name for f in through._meta.fields
                    if f.is_relation and f.related_model == Department
                )
                other_col = next(
                    f.name for f in through._meta.fields
                    if f.is_relation and f.related_model not in (Department, None)
                )
                for d in doomed:
                    for link in through.objects.filter(**{dept_col: d}):
                        other_id = getattr(link, other_col + '_id')
                        if through.objects.filter(
                            **{dept_col: survivor, other_col + '_id': other_id}
                        ).exists():
                            link.delete()
                        else:
                            setattr(link, dept_col, survivor)
                            link.save(update_fields=[dept_col])
            else:
                for d in doomed:
                    related_model.objects.filter(
                        **{field.name: d}
                    ).update(**{field.name: survivor})
