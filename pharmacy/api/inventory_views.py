"""
API views for inventory management
"""
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.template.loader import render_to_string
from ..models import Medication, Dispensary, MedicationInventory, ActiveStoreInventory
from ..views import user_has_inventory_edit_permission


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


def search_medication_inventory(request):
    """
    API endpoint to search medications in a specific dispensary inventory
    Returns filtered inventory items based on search query
    """
    if request.method == 'GET':
        dispensary_id = request.GET.get('dispensary_id')
        search_query = request.GET.get('search', '').strip()
        
        # Check if this is an HTMX request
        is_htmx = request.headers.get('HX-Request') == 'true'
        
        # Debug logging
        print(f"Search API called: dispensary_id={dispensary_id}, search_query='{search_query}', is_htmx={is_htmx}")
        
        if not dispensary_id:
            error_response = {
                'error': 'Dispensary ID is required'
            }
            print(f"Error: {error_response}")
            if is_htmx:
                html = render_to_string('pharmacy/partials/inventory_search_results.html', error_response, request=request)
                return HttpResponse(html)
            else:
                return JsonResponse(error_response)
        
        try:
            dispensary_id = int(dispensary_id)
            
            # Get dispensary
            try:
                dispensary = Dispensary.objects.get(id=dispensary_id, is_active=True)
                
                # Get inventory items from both ActiveStoreInventory and MedicationInventory
                active_store_items = ActiveStoreInventory.objects.filter(
                    active_store__dispensary=dispensary
                ).select_related('medication', 'active_store')
                
                legacy_items = MedicationInventory.objects.filter(
                    dispensary=dispensary
                ).select_related('medication', 'dispensary')
                
                # Normalize items into common structure
                inventory_items = []
                for item in active_store_items:
                    inventory_items.append({
                        'id': item.id,
                        'medication': item.medication,
                        'stock_quantity': item.stock_quantity,
                        'reorder_level': getattr(item, 'reorder_level', None),
                        'last_restock_date': getattr(item, 'last_restock_date', None),
                        'source': 'active_store',
                        'object': item,
                    })
                
                for item in legacy_items:
                    inventory_items.append({
                        'id': item.id,
                        'medication': item.medication,
                        'stock_quantity': item.stock_quantity,
                        'reorder_level': getattr(item, 'reorder_level', None),
                        'last_restock_date': item.last_restock_date,
                        'source': 'legacy',
                        'object': item,
                    })
                
                print(f"Found {len(inventory_items)} total inventory items before filtering")
                
                # Filter items based on search query
                if search_query:
                    filtered_items = []
                    for item in inventory_items:
                        medication = item['medication']
                        med_name = medication.name if medication and medication.name else ''
                        med_generic = medication.generic_name if medication and medication.generic_name else ''
                        med_manufacturer = medication.manufacturer if medication and medication.manufacturer else ''
                        
                        name_match = med_name and search_query.lower() in med_name.lower()
                        generic_match = med_generic and search_query.lower() in med_generic.lower()
                        manufacturer_match = med_manufacturer and search_query.lower() in med_manufacturer.lower()
                        
                        if name_match or generic_match or manufacturer_match:
                            filtered_items.append(item)
                    
                    inventory_items = filtered_items
                    print(f"Filtered to {len(inventory_items)} items matching '{search_query}'")
                
                # Check edit permissions
                can_edit_inventory = user_has_inventory_edit_permission(request.user, dispensary)
                
                # Prepare response data
                response_data = {
                    'success': True,
                    'items': [],
                    'total_count': len(inventory_items),
                    'dispensary_id': dispensary_id,
                    'dispensary': dispensary,
                    'can_edit_inventory': can_edit_inventory
                }
                
                for item in inventory_items:
                    medication = item['medication']
                    item_data = {
                        'id': item['id'],
                        'medication_id': medication.id if medication else None,
                        'medication_name': medication.name if medication and medication.name else 'Unknown',
                        'generic_name': medication.generic_name if medication and medication.generic_name else '',
                        'manufacturer': medication.manufacturer if medication and medication.manufacturer else '',
                        'strength': medication.strength if medication and medication.strength else '',
                        'dosage_form': medication.dosage_form if medication and medication.dosage_form else '',
                        'stock_quantity': item['stock_quantity'],
                        'reorder_level': item['reorder_level'] or 10,
                        'source': item['source'],
                        'last_restock_date': item['last_restock_date'].strftime('%Y-%m-%d') if item['last_restock_date'] else None,
                    }
                    response_data['items'].append(item_data)
                
            except Dispensary.DoesNotExist:
                response_data = {'error': 'Dispensary not found'}
            
        except Exception as e:
            response_data = {'error': f'Error searching inventory: {str(e)}'}
            print(f"Exception in search: {str(e)}")
        
        print(f"Final response_data keys: {response_data.keys()}")
        print(f"Response contains {len(response_data.get('items', []))} items")
        
        # Return HTML template fragment instead of JSON
        if is_htmx:
            try:
                html = render_to_string('pharmacy/partials/inventory_search_results.html', response_data, request=request)
                print(f"Generated HTML length: {len(html)}")
                print(f"HTML preview: {html[:200]}...")  # Show first 200 chars
                return HttpResponse(html)
            except Exception as template_error:
                print(f"Template rendering error: {template_error}")
                # Return JSON response as fallback
                return JsonResponse({
                    'error': f'Template rendering error: {str(template_error)}',
                    'debug_data': response_data
                })
        else:
            return JsonResponse(response_data)
    
    return JsonResponse({'error': 'Method not allowed'})
