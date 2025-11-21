from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from dental.models import DentalService


class Command(BaseCommand):
    help = 'Populate the dental module with comprehensive dental services and procedures'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing services with new prices and descriptions',
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Populate only a specific category (diagnostic, preventive, restorative, endodontic, periodontal, prosthodontic, surgery, orthodontic, pediatric, emergency)',
        )

    def handle(self, *args, **options):
        update = options.get('update', False)
        category_filter = options.get('category')

        self.stdout.write(self.style.SUCCESS('Starting to populate dental services...'))

        # Define all dental services with their categories, prices, and descriptions
        dental_services = {
            'diagnostic': [
                {
                    'name': 'Dental Examination/Consultation',
                    'price': Decimal('10000.00'),
                    'description': 'Comprehensive oral examination including dental charting, oral cancer screening, and treatment planning.'
                },
                {
                    'name': 'Bitewing X-Ray',
                    'price': Decimal('5000.00'),
                    'description': 'Bitewing radiographs for detection of interproximal caries and bone level assessment.'
                },
                {
                    'name': 'Periapical X-Ray',
                    'price': Decimal('5000.00'),
                    'description': 'Periapical radiograph showing full tooth structure and surrounding bone for diagnostic purposes.'
                },
                {
                    'name': 'Panoramic X-Ray (OPG)',
                    'price': Decimal('15000.00'),
                    'description': 'Panoramic radiograph providing full view of upper and lower jaws, teeth, and supporting structures.'
                },
                {
                    'name': 'Dental CT Scan (CBCT)',
                    'price': Decimal('50000.00'),
                    'description': 'Cone beam computed tomography for 3D imaging used in implant planning and complex cases.'
                },
                {
                    'name': 'Oral Cancer Screening',
                    'price': Decimal('8000.00'),
                    'description': 'Comprehensive oral soft tissue examination for early detection of oral cancer and precancerous lesions.'
                },
                {
                    'name': 'Study Models',
                    'price': Decimal('12000.00'),
                    'description': 'Diagnostic study models for treatment planning and documentation.'
                },
            ],
            'preventive': [
                {
                    'name': 'Scaling and Polishing (Prophylaxis)',
                    'price': Decimal('15000.00'),
                    'description': 'Professional dental cleaning including scaling of calculus and plaque removal, followed by polishing.'
                },
                {
                    'name': 'Fluoride Treatment',
                    'price': Decimal('5000.00'),
                    'description': 'Professional fluoride application for strengthening tooth enamel and preventing caries.'
                },
                {
                    'name': 'Fissure Sealants (per tooth)',
                    'price': Decimal('3000.00'),
                    'description': 'Application of protective sealant on pits and fissures of posterior teeth to prevent caries.'
                },
                {
                    'name': 'Oral Hygiene Instruction',
                    'price': Decimal('3000.00'),
                    'description': 'Personalized oral hygiene education including proper brushing and flossing techniques.'
                },
                {
                    'name': 'Desensitization Treatment',
                    'price': Decimal('8000.00'),
                    'description': 'Treatment for sensitive teeth using desensitizing agents.'
                },
            ],
            'restorative': [
                {
                    'name': 'Amalgam Filling (1 surface)',
                    'price': Decimal('10000.00'),
                    'description': 'Silver amalgam restoration for single surface cavity.'
                },
                {
                    'name': 'Amalgam Filling (2 surfaces)',
                    'price': Decimal('15000.00'),
                    'description': 'Silver amalgam restoration for two-surface cavity.'
                },
                {
                    'name': 'Amalgam Filling (3+ surfaces)',
                    'price': Decimal('20000.00'),
                    'description': 'Silver amalgam restoration for complex multi-surface cavity.'
                },
                {
                    'name': 'Composite Filling (1 surface)',
                    'price': Decimal('15000.00'),
                    'description': 'Tooth-colored composite restoration for single surface cavity.'
                },
                {
                    'name': 'Composite Filling (2 surfaces)',
                    'price': Decimal('20000.00'),
                    'description': 'Tooth-colored composite restoration for two-surface cavity.'
                },
                {
                    'name': 'Composite Filling (3+ surfaces)',
                    'price': Decimal('30000.00'),
                    'description': 'Tooth-colored composite restoration for complex multi-surface cavity.'
                },
                {
                    'name': 'Glass Ionomer Filling',
                    'price': Decimal('12000.00'),
                    'description': 'Glass ionomer cement restoration, ideal for pediatric patients and non-load bearing areas.'
                },
                {
                    'name': 'Temporary Filling',
                    'price': Decimal('5000.00'),
                    'description': 'Temporary restoration for intermediate treatment phases.'
                },
            ],
            'endodontic': [
                {
                    'name': 'Root Canal Treatment - Anterior Tooth',
                    'price': Decimal('50000.00'),
                    'description': 'Root canal therapy for front teeth (incisors and canines) including shaping, cleaning, and obturation.'
                },
                {
                    'name': 'Root Canal Treatment - Premolar',
                    'price': Decimal('70000.00'),
                    'description': 'Root canal therapy for premolar teeth including shaping, cleaning, and obturation.'
                },
                {
                    'name': 'Root Canal Treatment - Molar',
                    'price': Decimal('100000.00'),
                    'description': 'Root canal therapy for molar teeth including shaping, cleaning, and obturation of all canals.'
                },
                {
                    'name': 'Root Canal Re-treatment',
                    'price': Decimal('120000.00'),
                    'description': 'Non-surgical re-treatment of previously root canal treated tooth.'
                },
                {
                    'name': 'Apicoectomy',
                    'price': Decimal('80000.00'),
                    'description': 'Surgical root end resection and seal for failed root canal treatment.'
                },
            ],
            'periodontal': [
                {
                    'name': 'Deep Cleaning/Scaling and Root Planing (per quadrant)',
                    'price': Decimal('25000.00'),
                    'description': 'Non-surgical periodontal therapy including deep scaling and root planing.'
                },
                {
                    'name': 'Gingivectomy',
                    'price': Decimal('30000.00'),
                    'description': 'Surgical removal of gum tissue for treating gingival hyperplasia or pocket reduction.'
                },
                {
                    'name': 'Flap Surgery (per quadrant)',
                    'price': Decimal('60000.00'),
                    'description': 'Surgical periodontal flap procedure for deep cleaning and bone contouring.'
                },
                {
                    'name': 'Bone Grafting',
                    'price': Decimal('80000.00'),
                    'description': 'Placement of bone graft material for regenerative periodontal therapy.'
                },
                {
                    'name': 'Guided Tissue Regeneration',
                    'price': Decimal('100000.00'),
                    'description': 'Advanced regenerative procedure using membranes for periodontal tissue regeneration.'
                },
            ],
            'prosthodontic': [
                {
                    'name': 'Complete Denture - Upper',
                    'price': Decimal('120000.00'),
                    'description': 'Full upper denture prosthesis replacing all upper teeth.'
                },
                {
                    'name': 'Complete Denture - Lower',
                    'price': Decimal('100000.00'),
                    'description': 'Full lower denture prosthesis replacing all lower teeth.'
                },
                {
                    'name': 'Partial Denture - Acrylic',
                    'price': Decimal('60000.00'),
                    'description': 'Removable acrylic partial denture for replacing missing teeth.'
                },
                {
                    'name': 'Partial Denture - Metal Framework',
                    'price': Decimal('100000.00'),
                    'description': 'Removable partial denture with metal framework for better durability.'
                },
                {
                    'name': 'Porcelain Fused to Metal Crown',
                    'price': Decimal('80000.00'),
                    'description': 'PFM crown combining strength of metal with aesthetics of porcelain.'
                },
                {
                    'name': 'All Ceramic Crown',
                    'price': Decimal('100000.00'),
                    'description': 'Metal-free ceramic crown for optimal aesthetics.'
                },
                {
                    'name': 'Zirconia Crown',
                    'price': Decimal('120000.00'),
                    'description': 'High-strength zirconia crown for posterior teeth.'
                },
                {
                    'name': 'Fixed Bridge - 3 Units',
                    'price': Decimal('200000.00'),
                    'description': 'Fixed dental prosthesis replacing one missing tooth with three-unit bridge.'
                },
                {
                    'name': 'Dental Implant Placement',
                    'price': Decimal('250000.00'),
                    'description': 'Surgical placement of dental implant fixture for tooth replacement.'
                },
                {
                    'name': 'Implant Crown',
                    'price': Decimal('150000.00'),
                    'description': 'Final restoration placed on dental implant.'
                },
            ],
            'surgery': [
                {
                    'name': 'Simple Extraction',
                    'price': Decimal('8000.00'),
                    'description': 'Extraction of non-complicated tooth with forceps.'
                },
                {
                    'name': 'Surgical Extraction',
                    'price': Decimal('20000.00'),
                    'description': 'Complex extraction requiring surgical approach and bone removal.'
                },
                {
                    'name': 'Wisdom Tooth Removal - Soft Tissue',
                    'price': Decimal('25000.00'),
                    'description': 'Extraction of impacted wisdom tooth covered by soft tissue.'
                },
                {
                    'name': 'Wisdom Tooth Removal - Bony Impaction',
                    'price': Decimal('40000.00'),
                    'description': 'Surgical extraction of bony impacted wisdom tooth.'
                },
                {
                    'name': 'Biopsy - Soft Tissue',
                    'price': Decimal('20000.00'),
                    'description': 'Removal of soft tissue sample for histopathological examination.'
                },
                {
                    'name': 'Biopsy - Hard Tissue',
                    'price': Decimal('30000.00'),
                    'description': 'Removal of bone or tooth sample for histopathological examination.'
                },
                {
                    'name': 'Alveoloplasty',
                    'price': Decimal('30000.00'),
                    'description': 'Surgical contouring of alveolar bone for denture preparation.'
                },
                {
                    'name': 'Frenectomy',
                    'price': Decimal('15000.00'),
                    'description': 'Surgical removal or modification of frenum.'
                },
            ],
            'orthodontic': [
                {
                    'name': 'Orthodontic Consultation',
                    'price': Decimal('15000.00'),
                    'description': 'Comprehensive orthodontic examination including records and treatment planning.'
                },
                {
                    'name': 'Metal Braces - Full Mouth',
                    'price': Decimal('350000.00'),
                    'description': 'Complete orthodontic treatment with conventional metal braces.'
                },
                {
                    'name': 'Ceramic Braces - Full Mouth',
                    'price': Decimal('450000.00'),
                    'description': 'Complete orthodontic treatment with aesthetic ceramic braces.'
                },
                {
                    'name': 'Removable Retainer',
                    'price': Decimal('25000.00'),
                    'description': 'Custom removable orthodontic retainer for post-treatment maintenance.'
                },
                {
                    'name': 'Fixed Retainer',
                    'price': Decimal('20000.00'),
                    'description': 'Fixed wire retainer bonded to lingual surfaces of anterior teeth.'
                },
                {
                    'name': 'Space Maintainer',
                    'price': Decimal('25000.00'),
                    'description': 'Fixed or removable appliance to maintain space for permanent teeth.'
                },
            ],
            'pediatric': [
                {
                    'name': 'Pediatric Dental Examination',
                    'price': Decimal('8000.00'),
                    'description': 'Comprehensive dental examination for children including preventive counseling.'
                },
                {
                    'name': 'Pediatric Filling',
                    'price': Decimal('12000.00'),
                    'description': 'Tooth-colored filling for primary teeth.'
                },
                {
                    'name': 'Pulpotomy (Baby Root Canal)',
                    'price': Decimal('25000.00'),
                    'description': 'Vital pulp therapy for primary teeth.'
                },
                {
                    'name': 'Space Maintainer - Pediatric',
                    'price': Decimal('20000.00'),
                    'description': 'Appliance to maintain space after premature loss of primary teeth.'
                },
                {
                    'name': 'Fluoride Varnish Application',
                    'price': Decimal('4000.00'),
                    'description': 'Professional fluoride varnish application for caries prevention in children.'
                },
            ],
            'emergency': [
                {
                    'name': 'Emergency Consultation',
                    'price': Decimal('15000.00'),
                    'description': 'Urgent dental examination for acute dental problems.'
                },
                {
                    'name': 'Emergency Temporary Filling',
                    'price': Decimal('8000.00'),
                    'description': 'Temporary restoration for emergency pain relief.'
                },
                {
                    'name': 'Trauma Management',
                    'price': Decimal('30000.00'),
                    'description': 'Emergency treatment for dental trauma including repositioning and splinting.'
                },
                {
                    'name': 'Abscess Drainage',
                    'price': Decimal('20000.00'),
                    'description': 'Incision and drainage of dental abscess.'
                },
                {
                    'name': 'Emergency Extraction',
                    'price': Decimal('15000.00'),
                    'description': 'Urgent extraction for severe pain or infection.'
                },
            ],
        }

        try:
            with transaction.atomic():
                services_created = 0
                services_updated = 0

                # Process categories based on filter
                categories_to_process = [category_filter] if category_filter else dental_services.keys()

                for category in categories_to_process:
                    if category not in dental_services:
                        self.stdout.write(
                            self.style.WARNING(f'Unknown category: {category}. Skipping.')
                        )
                        continue

                    self.stdout.write(f'\nProcessing {category.upper()} services...')
                    
                    for service_data in dental_services[category]:
                        service_name = service_data['name']
                        service_price = service_data['price']
                        service_description = service_data['description']

                        # Check if service already exists
                        existing_service = DentalService.objects.filter(name=service_name).first()

                        if existing_service:
                            if update:
                                # Update existing service
                                existing_service.price = service_price
                                existing_service.description = service_description
                                existing_service.save()
                                services_updated += 1
                                self.stdout.write(f'  Updated: {service_name}')
                            else:
                                self.stdout.write(f'  Skipped (already exists): {service_name}')
                        else:
                            # Create new service
                            DentalService.objects.create(
                                name=service_name,
                                price=service_price,
                                description=service_description,
                                is_active=True
                            )
                            services_created += 1
                            self.stdout.write(f'  Created: {service_name}')

                # Summary
                self.stdout.write('\n' + '='*50)
                self.stdout.write(self.style.SUCCESS('Population completed successfully!'))
                self.stdout.write(f'Services created: {services_created}')
                self.stdout.write(f'Services updated: {services_updated}')
                self.stdout.write(f'Total services in database: {DentalService.objects.count()}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error occurred during population: {str(e)}')
            )
            raise
