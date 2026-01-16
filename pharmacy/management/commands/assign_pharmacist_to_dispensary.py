"""
Management command to assign pharmacists to dispensary locations.
This allows administrators to manage pharmacist-dispensary assignments.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from pharmacy.models import Dispensary, PharmacistDispensaryAssignment
from django.db import transaction
from datetime import datetime

CustomUser = get_user_model()


class Command(BaseCommand):
    help = 'Assign a pharmacist to a dispensary or manage pharmacist assignments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all current pharmacist assignments'
        )
        
        parser.add_argument(
            '--pharmacist',
            type=str,
            help='Username or phone number of the pharmacist'
        )
        
        parser.add_argument(
            '--dispensary',
            type=str,
            help='Dispensary name to assign the pharmacist to'
        )
        
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove pharmacist assignment (instead of adding)'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for assignment (YYYY-MM-DD format), defaults to today'
        )
        
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for assignment (YYYY-MM-DD format), only used with --remove'
        )
        
        parser.add_argument(
            '--clear-all',
            action='store_true',
            help='Clear all assignments for a pharmacist'
        )

    def handle(self, *args, **options):
        # List all pharmacist assignments
        if options['list']:
            self.list_assignments()
            return

        # Remove pharmacist assignment
        if options['remove']:
            self.remove_assignment(options)
            return
        elif options['clear_all']:
            self.clear_all_assignments(options)
            return

        # Add pharmacist assignment
        if options['pharmacist'] and options['dispensary']:
            self.add_assignment(options)
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Please provide both --pharmacist and --dispensary to add an assignment, "
                    "or use --list to see current assignments, or --remove to remove an assignment."
                )
            )

    def list_assignments(self):
        """List all active pharmacist dispensary assignments"""
        assignments = PharmacistDispensaryAssignment.objects.filter(is_active=True).select_related(
            'pharmacist', 'dispensary'
        ).order_by('dispensary__name', 'pharmacist__username')

        if not assignments.exists():
            self.stdout.write(self.style.SUCCESS("No active pharmacist assignments found."))
            return

        self.stdout.write(self.style.SUCCESS("\n=== Active Pharmacist Assignments ==="))
        self.stdout.write(f"{'Dispensary':<30} {'Pharmacist':<25} {'Start Date':<12} {'Status':<10}")
        self.stdout.write("-" * 80)

        for assignment in assignments:
            pharmacist_name = assignment.pharmacist.get_full_name() or assignment.pharmacist.username
            self.stdout.write(
                f"{assignment.dispensary.name:<30} {pharmacist_name:<25} {assignment.start_date:<12} {'Active':<10}"
            )

    def find_pharmacist(self, pharmacist_identifier):
        """Find pharmacist by username or phone number"""
        try:
            # Try username first
            pharmacist = CustomUser.objects.filter(username=pharmacist_identifier).first()
            if pharmacist:
                return pharmacist
            
            # Try phone number
            pharmacist = CustomUser.objects.filter(phone_number=pharmacist_identifier).first()
            if pharmacist:
                return pharmacist
            
            # Try email
            pharmacist = CustomUser.objects.filter(email=pharmacist_identifier).first()
            if pharmacist:
                return pharmacist
                
            # Try name lookup
            pharmacist = CustomUser.objects.filter(first_name__icontains=pharmacist_identifier).first()
            if pharmacist:
                return pharmacist
                
            self.stdout.write(self.style.ERROR(f"Pharmacist not found: {pharmacist_identifier}"))
            return None
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error finding pharmacist: {e}"))
            return None

    def find_dispensary(self, dispensary_name):
        """Find dispensary by name"""
        try:
            dispensary = Dispensary.objects.filter(name__icontains=dispensary_name, is_active=True).first()
            if not dispensary:
                self.stdout.write(self.style.ERROR(f"Dispensary not found: {dispensary_name}"))
                return None
            return dispensary
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error finding dispensary: {e}"))
            return None

    def parse_date(self, date_str):
        """Parse date string to date object"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            self.stdout.write(self.style.ERROR(f"Invalid date format: {date_str}. Use YYYY-MM-DD format."))
            return None

    def add_assignment(self, options):
        """Add or update pharmacist dispensary assignment"""
        with transaction.atomic():
            pharmacist = self.find_pharmacist(options['pharmacist'])
            if not pharmacist:
                return

            dispensary = self.find_dispensary(options['dispensary'])
            if not dispensary:
                return

            # Check if pharmacist has pharmacist role
            if not pharmacist.is_pharmacist:
                # Check roles
                user_roles = list(pharmacist.roles.values_list('name', flat=True))
                if 'pharmacist' not in user_roles and hasattr(pharmacist, 'profile') and pharmacist.profile:
                    if pharmacist.profile.role != 'pharmacist':
                        self.stdout.write(
                            self.style.WARNING(
                                f"User '{pharmacist.username}' does not have pharmacist role. "
                                "Assigning anyway, but user won't be able to access pharmacy module."
                            )
                        )
                elif 'pharmacist' not in user_roles:
                    self.stdout.write(
                        self.style.ERROR(
                            f"User '{pharmacist.username}' does not have pharmacist role. Cannot assign to dispensary."
                        )
                    )
                    return

            # Check existing assignment
            existing = PharmacistDispensaryAssignment.objects.filter(
                pharmacist=pharmacist,
                dispensary=dispensary,
                end_date__isnull=True
            ).first()

            if existing:
                if existing.is_active:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Pharmacist '{pharmacist.get_full_name()}' is already assigned to "
                            f"'{dispensary.name}' (since {existing.start_date})."
                        )
                    )
                    return
                else:
                    # Reactivate existing assignment
                    existing.is_active = True
                    existing.end_date = None
                    existing.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Reactivated assignment: {pharmacist.get_full_name()} -> {dispensary.name}"
                        )
                    )
                    return

            # Check if pharmacist already has an active assignment to this or other dispensary
            active_assignments = PharmacistDispensaryAssignment.objects.filter(
                pharmacist=pharmacist,
                is_active=True,
                end_date__isnull=True
            )

            if active_assignments.exists():
                if options.get('force'):
                    # End the current active assignment
                    active_assignments.update(end_date=timezone.now().date(), is_active=False)
                    self.stdout.write(
                        self.style.WARNING(
                            f"Ended existing active assignment(s) for {pharmacist.get_full_name()}."
                        )
                    )
                else:
                    current_dispensary = active_assignments.first().dispensary.name
                    self.stdout.write(
                        self.style.ERROR(
                            f"Pharmacist '{pharmacist.get_full_name()}' already has an active assignment "
                            f"to '{current_dispensary}'. Use --force to override."
                        )
                    )
                    return

            # Get start date
            start_date = timezone.now().date()
            if options['start_date']:
                parsed_date = self.parse_date(options['start_date'])
                if parsed_date:
                    start_date = parsed_date
                else:
                    return

            # Create new assignment
            assignment = PharmacistDispensaryAssignment.objects.create(
                pharmacist=pharmacist,
                dispensary=dispensary,
                start_date=start_date,
                is_active=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully assigned '{pharmacist.get_full_name()}' to '{dispensary.name}' "
                    f"(since {assignment.start_date})."
                )
            )

    def remove_assignment(self, options):
        """Remove pharmacist dispensary assignment"""
        with transaction.atomic():
            pharmacist = self.find_pharmacist(options['pharmacist'])
            if not pharmacist:
                return

            dispensary = None
            if options['dispensary']:
                dispensary = self.find_dispensary(options['dispensary'])
                if not dispensary:
                    return

            if dispensary:
                # Remove specific assignment
                assignments = PharmacistDispensaryAssignment.objects.filter(
                    pharmacist=pharmacist,
                    dispensary=dispensary,
                    is_active=True,
                    end_date__isnull=True
                )
                
                if not assignments.exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"No active assignment found for {pharmacist.get_full_name()} to {dispensary.name}."
                        )
                    )
                    return

                end_date = timezone.now().date()
                if options['end_date']:
                    parsed_date = self.parse_date(options['end_date'])
                    if parsed_date:
                        end_date = parsed_date
                    else:
                        return

                assignments.update(end_date=end_date, is_active=False)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Removed assignment: {pharmacist.get_full_name()} -> {dispensary.name} "
                        f"(ended {end_date})."
                    )
                )
            else:
                # Remove all assignments for the pharmacist
                assignments = PharmacistDispensaryAssignment.objects.filter(
                    pharmacist=pharmacist,
                    is_active=True,
                    end_date__isnull=True
                )

                if not assignments.exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"No active assignments found for {pharmacist.get_full_name()}."
                        )
                    )
                    return

                end_date = timezone.now().date()
                if options['end_date']:
                    parsed_date = self.parse_date(options['end_date'])
                    if parsed_date:
                        end_date = parsed_date
                    else:
                        return

                count = assignments.count()
                assignments.update(end_date=end_date, is_active=False)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Removed {count} assignment(s) for {pharmacist.get_full_name()} (ended {end_date})."
                    )
                )

    def clear_all_assignments(self, options):
        """Clear ALL assignments for a pharmacist (use with caution)"""
        pharmacist = self.find_pharmacist(options['pharmacist'])
        if not pharmacist:
            return

        assignments = PharmacistDispensaryAssignment.objects.filter(pharmacist=pharmacist)
        
        if not assignments.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"No assignments found for {pharmacist.get_full_name()}."
                )
            )
            return

        count = assignments.count()
        assignments.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Permanently deleted {count} assignment(s) for {pharmacist.get_full_name()}."
            )
        )
