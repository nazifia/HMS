from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from ..models import Medication, MedicationCategory, Supplier, Prescription, PrescriptionItem
from .serializers import (
    MedicationSerializer, MedicationCategorySerializer, SupplierSerializer,
    PrescriptionSerializer, PrescriptionItemSerializer
)

class MedicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing medications.
    """
    queryset = Medication.objects.filter(is_active=True)
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Medication.objects.filter(is_active=True)
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

class MedicationCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing medication categories.
    """
    queryset = MedicationCategory.objects.all()
    serializer_class = MedicationCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing suppliers.
    """
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

class PrescriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing prescriptions.
    """
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Prescription.objects.all()
        patient = self.request.query_params.get('patient', None)
        doctor = self.request.query_params.get('doctor', None)
        status = self.request.query_params.get('status', None)
        
        if patient:
            queryset = queryset.filter(patient__id=patient)
            
        if doctor:
            queryset = queryset.filter(doctor__id=doctor)
            
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset

class PrescriptionItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing prescription items.
    """
    queryset = PrescriptionItem.objects.all()
    serializer_class = PrescriptionItemSerializer
    permission_classes = [permissions.IsAuthenticated]