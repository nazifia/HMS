from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from pharmacy.models import DispensingLog, Prescription, Medication
from decimal import Decimal
from datetime import timedelta

class Command(BaseCommand):
    help = 'Generate pharmacy sales and dispensing reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to generate report for (default: 30)'
        )
        parser.add_argument(
            '--format',
            choices=['text', 'csv'],
            default='text',
            help='Output format (default: text)'
        )

    def handle(self, *args, **options):
        days = options['days']
        format = options['format']
        
        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(f'Generating pharmacy report for {start_date} to {end_date}...')
        )
        
        # Get dispensing data
        dispensing_logs = DispensingLog.objects.filter(
            dispensed_date__date__gte=start_date,
            dispensed_date__date__lte=end_date
        ).select_related(
            'prescription_item__medication',
            'prescription_item__prescription__patient',
            'dispensed_by',
            'dispensary'
        )
        
        if not dispensing_logs.exists():
            self.stdout.write(
                self.style.WARNING('No dispensing activity found in the specified period.')
            )
            return
        
        # Calculate statistics
        total_medications_dispensed = dispensing_logs.aggregate(
            total_quantity=models.Sum('dispensed_quantity')
        )['total_quantity'] or 0
        
        total_sales = dispensing_logs.aggregate(
            total_sales=models.Sum('total_price_for_this_log')
        )['total_sales'] or Decimal('0.00')
        
        unique_patients = dispensing_logs.values(
            'prescription_item__prescription__patient'
        ).distinct().count()
        
        unique_medications = dispensing_logs.values(
            'prescription_item__medication'
        ).distinct().count()
        
        # Top medications by quantity
        top_medications = dispensing_logs.values(
            'prescription_item__medication__name'
        ).annotate(
            total_quantity=models.Sum('dispensed_quantity'),
            total_sales=models.Sum('total_price_for_this_log')
        ).order_by('-total_quantity')[:10]
        
        # Top dispensaries by sales
        top_dispensaries = dispensing_logs.values(
            'dispensary__name'
        ).annotate(
            total_sales=models.Sum('total_price_for_this_log'),
            total_items=models.Sum('dispensed_quantity')
        ).order_by('-total_sales')[:10]
        
        # Output based on format
        if format == 'text':
            self.output_text_report(
                start_date, end_date, total_medications_dispensed, total_sales,
                unique_patients, unique_medications, top_medications, top_dispensaries
            )
        elif format == 'csv':
            self.output_csv_report(dispensing_logs)

    def output_text_report(self, start_date, end_date, total_medications_dispensed, 
                          total_sales, unique_patients, unique_medications, 
                          top_medications, top_dispensaries):
        \"\"\"Output report in text format\"\"\"
        self.stdout.write('\n' + '='*60)
        self.stdout.write('PHARMACY SALES AND DISPENSING REPORT')
        self.stdout.write('='*60)
        self.stdout.write(f'Period: {start_date} to {end_date}')
        self.stdout.write('='*60)
        
        self.stdout.write(f'\nSUMMARY STATISTICS:')
        self.stdout.write(f'  Total Medications Dispensed: {total_medications_dispensed:,}')
        self.stdout.write(f'  Total Sales: ₦{total_sales:,.2f}')
        self.stdout.write(f'  Unique Patients Served: {unique_patients:,}')
        self.stdout.write(f'  Unique Medications Dispensed: {unique_medications:,}')
        
        self.stdout.write(f'\nTOP 10 MEDICATIONS BY QUANTITY:')
        self.stdout.write('  Medication Name'.ljust(30) + 'Quantity'.rjust(15) + 'Sales'.rjust(15))
        self.stdout.write('-' * 60)
        for med in top_medications:
            self.stdout.write(
                f'  {med[\"prescription_item__medication__name\"][:28]:<28} '
                f'{med[\"total_quantity\"]:>15,} '
                f'₦{med[\"total_sales\"]:>13,.2f}'
            )
        
        self.stdout.write(f'\nTOP 10 DISPENSARIES BY SALES:')
        self.stdout.write('  Dispensary Name'.ljust(30) + 'Sales'.rjust(15) + 'Items'.rjust(15))
        self.stdout.write('-' * 60)
        for disp in top_dispensaries:
            self.stdout.write(
                f'  {disp[\"dispensary__name\"][:28]:<28} '
                f'₦{disp[\"total_sales\"]:>13,.2f} '
                f'{disp[\"total_items\"]:>15,}'
            )
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('REPORT GENERATED SUCCESSFULLY')
        self.stdout.write('='*60)

    def output_csv_report(self, dispensing_logs):
        \"\"\"Output detailed report in CSV format\"\"\"
        import csv
        from django.http import HttpResponse
        from io import StringIO
        
        # Create in-memory CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Date', 'Patient', 'Medication', 'Quantity', 'Unit Price', 
            'Total Price', 'Dispensed By', 'Dispensary'
        ])
        
        # Write data
        for log in dispensing_logs:
            writer.writerow([
                log.dispensed_date.strftime('%Y-%m-%d'),
                log.prescription_item.prescription.patient.get_full_name(),
                log.prescription_item.medication.name,
                log.dispensed_quantity,
                log.unit_price_at_dispense,
                log.total_price_for_this_log,
                log.dispensed_by.get_full_name() if log.dispensed_by else 'N/A',
                log.dispensary.name if log.dispensary else 'N/A'
            ])
        
        # Output CSV content
        self.stdout.write(output.getvalue())