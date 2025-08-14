from django.core.management.base import BaseCommand
from laboratory.models import Test, TestParameter


class Command(BaseCommand):
    help = 'Add sample test parameters for testing the modal functionality'

    def handle(self, *args, **options):
        # Get the first few tests
        tests = Test.objects.all()[:5]
        
        if not tests:
            self.stdout.write(self.style.ERROR('No tests found. Please create some tests first.'))
            return
        
        # Sample parameters for different types of tests
        sample_parameters = {
            'Blood': [
                {'name': 'Hemoglobin', 'unit': 'g/dL', 'normal_range': '12.0-16.0', 'order': 1},
                {'name': 'White Blood Cell Count', 'unit': '/μL', 'normal_range': '4000-11000', 'order': 2},
                {'name': 'Red Blood Cell Count', 'unit': 'million/μL', 'normal_range': '4.5-5.5', 'order': 3},
                {'name': 'Platelet Count', 'unit': '/μL', 'normal_range': '150000-450000', 'order': 4},
                {'name': 'Hematocrit', 'unit': '%', 'normal_range': '36-46', 'order': 5},
            ],
            'Urine': [
                {'name': 'Protein', 'unit': 'mg/dL', 'normal_range': '0-8', 'order': 1},
                {'name': 'Glucose', 'unit': 'mg/dL', 'normal_range': '0-15', 'order': 2},
                {'name': 'Specific Gravity', 'unit': '', 'normal_range': '1.003-1.030', 'order': 3},
                {'name': 'pH', 'unit': '', 'normal_range': '4.6-8.0', 'order': 4},
            ],
            'Chemistry': [
                {'name': 'Glucose', 'unit': 'mg/dL', 'normal_range': '70-100', 'order': 1},
                {'name': 'Creatinine', 'unit': 'mg/dL', 'normal_range': '0.6-1.2', 'order': 2},
                {'name': 'Blood Urea Nitrogen', 'unit': 'mg/dL', 'normal_range': '7-20', 'order': 3},
                {'name': 'Total Cholesterol', 'unit': 'mg/dL', 'normal_range': '<200', 'order': 4},
                {'name': 'HDL Cholesterol', 'unit': 'mg/dL', 'normal_range': '>40', 'order': 5},
                {'name': 'LDL Cholesterol', 'unit': 'mg/dL', 'normal_range': '<100', 'order': 6},
            ]
        }
        
        created_count = 0
        
        for test in tests:
            # Determine which parameter set to use based on test name or sample type
            param_set = None
            test_name_lower = test.name.lower()
            sample_type_lower = test.sample_type.lower() if test.sample_type else ''
            
            if 'blood' in test_name_lower or 'cbc' in test_name_lower or 'hemoglobin' in test_name_lower:
                param_set = sample_parameters['Blood']
            elif 'urine' in test_name_lower or 'urine' in sample_type_lower:
                param_set = sample_parameters['Urine']
            elif 'chemistry' in test_name_lower or 'glucose' in test_name_lower or 'cholesterol' in test_name_lower:
                param_set = sample_parameters['Chemistry']
            else:
                # Default to chemistry panel
                param_set = sample_parameters['Chemistry'][:3]  # Just first 3 parameters
            
            # Add parameters to the test
            for param_data in param_set:
                parameter, created = TestParameter.objects.get_or_create(
                    test=test,
                    name=param_data['name'],
                    defaults={
                        'unit': param_data['unit'],
                        'normal_range': param_data['normal_range'],
                        'order': param_data['order']
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'Created parameter: {parameter.name} for test: {test.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} test parameters.')
        )
