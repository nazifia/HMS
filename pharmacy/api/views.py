from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum
from ..models import (
    Medication, MedicationCategory, Supplier, Prescription, PrescriptionItem,
    Dispensary, ActiveStoreInventory,
)
from .serializers import (
    MedicationSerializer, MedicationCategorySerializer, SupplierSerializer,
    PrescriptionSerializer, PrescriptionItemSerializer, DispensarySerializer,
)
from ..inter_dispensary_forms import InterDispensaryTransferForm


class PharmacyPagination(PageNumberPagination):
    """Applied per-viewset, not globally: the accounts API already ships
    unpaginated lists and callers would break on the envelope change."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

class MedicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing medications.
    """
    queryset = Medication.objects.filter(is_active=True)
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PharmacyPagination

    def get_queryset(self):
        queryset = Medication.objects.select_related('category').filter(is_active=True)
        search = self.request.query_params.get('search', None)
        category = self.request.query_params.get('category', None)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(generic_name__icontains=search) |
                Q(category__name__icontains=search)
            )
            
        if category:
            queryset = queryset.filter(category__id=category)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """Autocomplete endpoint for medication names"""
        query = request.query_params.get('q', '')
        if query and len(query) >= 2:
            medications = Medication.objects.filter(
                name__icontains=query, is_active=True
            )[:10]
            return Response([
                {
                    'id': med.id,
                    'name': med.name,
                    'strength': med.strength,
                    'price': str(med.price)
                }
                for med in medications
            ])
        return Response([])

    @action(detail=True, methods=['get'])
    def stock(self, request, pk=None):
        """Stock for this medication in every active dispensary."""
        medication = self.get_object()
        by_store = {
            row['active_store__dispensary']: row['total']
            for row in ActiveStoreInventory.objects
            .filter(medication=medication)
            .values('active_store__dispensary')
            .annotate(total=Sum('stock_quantity'))
        }
        return Response([
            {
                'dispensary_id': d.id,
                'dispensary': d.name,
                'stock_quantity': by_store.get(d.id, 0),
            }
            for d in Dispensary.objects.filter(is_active=True).order_by('name')
        ])


class DispensaryViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing dispensaries."""
    queryset = Dispensary.objects.filter(is_active=True).order_by('name')
    serializer_class = DispensarySerializer
    permission_classes = [permissions.IsAuthenticated]


class MedicationCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing medication categories.
    """
    queryset = MedicationCategory.objects.all()
    serializer_class = MedicationCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class SupplierViewSet(viewsets.ModelViewSet):
    """
    API endpoint for suppliers.

    Reading needs only a session/token; adding or editing needs the
    pharmacy.add_supplier / change_supplier permission, so holding
    `pharmacy.view` does not imply write access.
    """
    queryset = Supplier.objects.filter(is_active=True).order_by('name')
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = Supplier.objects.filter(is_active=True).order_by('name')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

class PrescriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing prescriptions.
    """
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PharmacyPagination

    def get_queryset(self):
        queryset = (
            Prescription.objects
            .select_related('patient', 'doctor')
            .prefetch_related('items__medication__category')
            .order_by('-prescription_date')
        )
        patient = self.request.query_params.get('patient', None)
        doctor = self.request.query_params.get('doctor', None)
        status = self.request.query_params.get('status', None)
        payment_status = self.request.query_params.get('payment_status', None)
        search = self.request.query_params.get('search', None)

        if patient:
            queryset = queryset.filter(patient__id=patient)

        if doctor:
            queryset = queryset.filter(doctor__id=doctor)

        if status:
            queryset = queryset.filter(status=status)

        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        if search:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(patient__patient_id__icontains=search) |
                Q(diagnosis__icontains=search)
            )

        return queryset

class PrescriptionItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing prescription items.
    """
    queryset = PrescriptionItem.objects.all()
    serializer_class = PrescriptionItemSerializer
    permission_classes = [permissions.IsAuthenticated]