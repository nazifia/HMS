"""
API views for inventory management
"""
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from ..models import Medication, Dispensary, MedicationInventory


@method_decorator(csrf_exempt, name='dispatch')
def check_medication_inventory(request):
    """
    API endpoint to check medication inventory availability for transfer
    """
    if request.method == 'GET':
        medication_id = request.GET.get('medication_id')
        dispensary_id = request.GET.get('dispensary_id')
        quantity = request.GET.get('quantity', '1')
        
        if not medication_id or not dispensary_id:
            return JsonResponse({
                'error': 'Medication ID and dispensary ID are required'
            })
        
        try:
            # Convert quantities to integers
            medication_id = int(medication_id)
            dispensary_id = int(dispensary_id)
            quantity = int(quantity)
            
            # Get medication and dispensary objects
            try:
                medication = Medication.objects.get(id=medication_id, is_active=True)
                dispensary = Dispensary.objects.get(id=dispensary_id, is_active=True)
                
                # Get inventory for the medication
                try:
                    inventory = MedicationInventory.objects.get(
                        medication=medication,
                        dispensary=dispensary
                    )
                    
                    quantity_available = inventory.stock_quantity
                    required_quantity = quantity
                    feasible = quantity_available >= required_quantity
                    
                    # Determine status color
                    if feasible:
                        status = 'success'
                        message = f'Transfer feasible: {quantity_available} units available'
                    else:
                        status = 'warning'
                        message = f'Insufficient stock: Only {quantity_available} units available'
                    
                    response_data = {
                        'medication': medication.name,
                        'medication_id': medication.id,
                        'dispensary': dispensary.name,
                        'dispensary_id': dispensary.id,
                        'available': quantity_available,
                        'required': required_quantity,
                        'feasible': feasible,
                        'status': status,
                        'message': message
                    }
                    
                except MedicationInventory.DoesNotExist:
                    response_data = {
                        'error': f'No inventory record found for {medication.name} in {dispensary.name}'
                    }
                
            except Medication.DoesNotExist:
                response_data = {'error': 'Medication not found'}
            except Dispensary.DoesNotExist:
                response_data = {'error': 'Dispensary not found'}
            except ValueError:
                response_data = {'error': 'Invalid medication or dispensary ID'}
            
        except Exception as e:
            response_data = {'error': f'Error checking inventory: {str(e)}'}
        
        return JsonResponse(response_data)
    
    return JsonResponse({'error': 'Method not allowed'})
