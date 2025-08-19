from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from patients.models import Patient
from core.medical_prescription_forms import MedicalModulePrescriptionForm, PrescriptionItemFormSet
from pharmacy.models import Prescription, PrescriptionItem

from .models import (
    OperationTheatre,
    SurgeryType,
    Surgery,
    SurgicalTeam,
    SurgicalEquipment,
    EquipmentUsage,
    SurgerySchedule,
    PostOperativeNote,
    PreOperativeChecklist,
    SurgeryLog
)
from accounts.models import CustomUser
from .forms import (
    OperationTheatreForm, 
    SurgeryTypeForm, 
    SurgeryForm, 
    SurgicalTeamFormSet,
    SurgicalEquipmentForm,
    EquipmentUsageFormSet,
    SurgeryScheduleForm,
    PostOperativeNoteForm,
    SurgeryFilterForm,
    PreOperativeChecklistForm
)

# Operation Theatre Views
class OperationTheatreListView(LoginRequiredMixin, ListView):
    model = OperationTheatre
    template_name = 'theatre/theatre_list.html'
    context_object_name = 'theatres'

class OperationTheatreDetailView(LoginRequiredMixin, DetailView):
    model = OperationTheatre
    template_name = 'theatre/theatre_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get upcoming surgeries for this theatre
        context['upcoming_surgeries'] = self.object.surgeries.filter(
            scheduled_date__gte=timezone.now(),
            status__in=['scheduled', 'in_progress']
        ).order_by('scheduled_date')[:5]
        return context

class OperationTheatreCreateView(LoginRequiredMixin, CreateView):
    model = OperationTheatre
    form_class = OperationTheatreForm
    template_name = 'theatre/theatre_form.html'
    success_url = reverse_lazy('theatre:theatre_list')

class OperationTheatreUpdateView(LoginRequiredMixin, UpdateView):
    model = OperationTheatre
    form_class = OperationTheatreForm
    template_name = 'theatre/theatre_form.html'
    success_url = reverse_lazy('theatre:theatre_list')

class OperationTheatreDeleteView(LoginRequiredMixin, DeleteView):
    model = OperationTheatre
    template_name = 'theatre/theatre_confirm_delete.html'
    success_url = reverse_lazy('theatre:theatre_list')

# Surgery Type Views
class SurgeryTypeListView(LoginRequiredMixin, ListView):
    model = SurgeryType
    template_name = 'theatre/surgery_type_list.html'
    context_object_name = 'surgery_types'

class SurgeryTypeDetailView(LoginRequiredMixin, DetailView):
    model = SurgeryType
    template_name = 'theatre/surgery_type_detail.html'

class SurgeryTypeCreateView(LoginRequiredMixin, CreateView):
    model = SurgeryType
    form_class = SurgeryTypeForm
    template_name = 'theatre/surgery_type_form.html'
    success_url = reverse_lazy('theatre:surgery_type_list')

class SurgeryTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = SurgeryType
    form_class = SurgeryTypeForm
    template_name = 'theatre/surgery_type_form.html'
    success_url = reverse_lazy('theatre:surgery_type_list')

class SurgeryTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = SurgeryType
    template_name = 'theatre/surgery_type_confirm_delete.html'
    success_url = reverse_lazy('theatre:surgery_type_list')

# Surgery Views
class SurgeryListView(LoginRequiredMixin, ListView):
    model = Surgery
    template_name = 'theatre/surgery_list.html'
    context_object_name = 'surgeries'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filter_form = SurgeryFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            if self.filter_form.cleaned_data.get('start_date'):
                queryset = queryset.filter(scheduled_date__gte=self.filter_form.cleaned_data['start_date'])
            if self.filter_form.cleaned_data.get('end_date'):
                queryset = queryset.filter(scheduled_date__lte=self.filter_form.cleaned_data['end_date'])
            if self.filter_form.cleaned_data.get('status'):
                queryset = queryset.filter(status=self.filter_form.cleaned_data['status'])
            if self.filter_form.cleaned_data.get('surgeon'):
                queryset = queryset.filter(primary_surgeon=self.filter_form.cleaned_data['surgeon'])
            if self.filter_form.cleaned_data.get('theatre'):
                queryset = queryset.filter(theatre=self.filter_form.cleaned_data['theatre'])
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        return context

class SurgeryDetailView(LoginRequiredMixin, DetailView):
    model = Surgery
    template_name = 'theatre/surgery_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        surgery = self.get_object()
        context['post_op_notes'] = surgery.post_op_notes.all()
        context['pre_op_checklist'] = None
        context['checklist_form'] = None

        try:
            context['pre_op_checklist'] = surgery.pre_op_checklist
            context['checklist_form'] = PreOperativeChecklistForm(instance=surgery.pre_op_checklist)
        except PreOperativeChecklist.DoesNotExist:
            context['checklist_form'] = PreOperativeChecklistForm()

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            pre_op_checklist = self.object.pre_op_checklist
            form = PreOperativeChecklistForm(request.POST, instance=pre_op_checklist)
        except PreOperativeChecklist.DoesNotExist:
            form = PreOperativeChecklistForm(request.POST)

        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.surgery = self.object
            checklist.completed_by = request.user
            checklist.save()
            messages.success(request, 'Pre-operative checklist updated successfully.')
            return redirect('theatre:surgery_detail', pk=self.object.pk)
        else:
            messages.error(request, 'Error updating pre-operative checklist.')
            return self.render_to_response(self.get_context_data(checklist_form=form))

class PreOperativeChecklistCreateView(LoginRequiredMixin, CreateView):
    model = PreOperativeChecklist
    form_class = PreOperativeChecklistForm
    template_name = 'theatre/pre_op_checklist_form.html'

    def form_valid(self, form):
        surgery = get_object_or_404(Surgery, pk=self.kwargs['surgery_id'])
        form.instance.surgery = surgery
        form.instance.completed_by = self.request.user
        messages.success(self.request, 'Pre-operative checklist created successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('theatre:surgery_detail', kwargs={'pk': self.kwargs['surgery_id']})

class SurgeryLogListView(LoginRequiredMixin, ListView):
    model = SurgeryLog
    template_name = 'theatre/surgery_log_list.html'
    context_object_name = 'logs'

    def get_queryset(self):
        surgery = get_object_or_404(Surgery, pk=self.kwargs['surgery_id'])
        return SurgeryLog.objects.filter(surgery=surgery).order_by('timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['surgery'] = get_object_or_404(Surgery, pk=self.kwargs['surgery_id'])
        return context

class SurgeryCreateView(LoginRequiredMixin, CreateView):
    model = Surgery
    form_class = SurgeryForm
    template_name = 'theatre/surgery_form.html'
    success_url = reverse_lazy('theatre:surgery_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if 'team_formset' not in kwargs:
            if self.request.POST:
                data['team_formset'] = SurgicalTeamFormSet(self.request.POST)
            else:
                data['team_formset'] = SurgicalTeamFormSet()
        if 'equipment_formset' not in kwargs:
            if self.request.POST:
                data['equipment_formset'] = EquipmentUsageFormSet(self.request.POST)
            else:
                data['equipment_formset'] = EquipmentUsageFormSet()
        return data

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        team_formset = SurgicalTeamFormSet(self.request.POST)
        equipment_formset = EquipmentUsageFormSet(self.request.POST)
        if form.is_valid() and team_formset.is_valid() and equipment_formset.is_valid():
            return self.form_valid(form, team_formset, equipment_formset)
        else:
            return self.form_invalid(form, team_formset, equipment_formset)

    def form_valid(self, form, team_formset, equipment_formset):
        from decimal import Decimal
        from billing.models import Invoice, InvoiceItem, Service, ServiceCategory
        from datetime import timedelta
        
        # Get authorization code if provided
        authorization_code_id = self.request.POST.get('authorization_code')
        authorization_code = None
        if authorization_code_id:
            try:
                from nhia.models import AuthorizationCode
                authorization_code = AuthorizationCode.objects.get(id=authorization_code_id)
                # Verify the authorization code is valid
                if not authorization_code.is_valid():
                    messages.error(self.request, "The provided authorization code is not valid.")
                    return self.form_invalid(form, team_formset, equipment_formset)
                # Verify the authorization code is for this patient
                if authorization_code.patient != form.cleaned_data['patient']:
                    messages.error(self.request, "The provided authorization code is not for this patient.")
                    return self.form_invalid(form, team_formset, equipment_formset)
            except AuthorizationCode.DoesNotExist:
                messages.error(self.request, "The provided authorization code does not exist.")
                return self.form_invalid(form, team_formset, equipment_formset)
        
        with transaction.atomic():
            self.object = form.save()
            team_formset.instance = self.object
            team_formset.save()
            equipment_formset.instance = self.object
            equipment_formset.save()
            
            # Create an invoice for this surgery
            subtotal = Decimal('0.00')  # For now, we'll set this to 0 as surgeries might have complex pricing
            tax_amount = Decimal('0.00')
            total_amount = subtotal + tax_amount
            due_date = self.object.scheduled_date.date() + timedelta(days=7) # Example: due in 7 days

            # If authorization code is provided, mark as paid
            invoice_status = 'paid' if authorization_code else 'pending'
            payment_method = 'insurance' if authorization_code else None
            payment_date = timezone.now().date() if authorization_code else None

            invoice = Invoice.objects.create(
                patient=self.object.patient,
                invoice_date=self.object.scheduled_date.date(),
                due_date=due_date,
                status=invoice_status, # Mark as paid if authorization code is used
                subtotal=subtotal,
                tax_amount=tax_amount,
                total_amount=total_amount,
                amount_paid=total_amount if authorization_code else Decimal('0.00'),
                payment_method=payment_method,
                payment_date=payment_date,
                created_by=self.request.user,
                source_app='theatre'
            )
            
            # Update surgery with invoice and authorization code
            self.object.invoice = invoice
            self.object.authorization_code = authorization_code
            self.object.status = 'scheduled' if authorization_code else 'pending'
            self.object.save()
            
            # Create a generic InvoiceItem for the surgery
            theatre_service_category, _ = ServiceCategory.objects.get_or_create(name="Theatre Services")
            service, _ = Service.objects.get_or_create(
                name=f"Theatre Procedure: {self.object.surgery_type.name}", 
                category=theatre_service_category,
                defaults={'price': Decimal('0.00'), 'description': f"Theatre procedure: {self.object.surgery_type.name}"}
            )

            InvoiceItem.objects.create(
                invoice=invoice,
                service=service, 
                description=f"Theatre Procedure: {self.object.surgery_type.name}",
                quantity=1,
                unit_price=Decimal('0.00'),
                tax_percentage=service.tax_percentage,
                tax_amount=Decimal('0.00'),
                total_amount=Decimal('0.00')
            )
            
            # If authorization code was used, mark it as used
            if authorization_code:
                authorization_code.mark_as_used(f"Surgery #{self.object.id}")
            
        messages.success(self.request, f'Surgery created successfully. Invoice #{invoice.invoice_number} generated and is {"paid via authorization code" if authorization_code else "pending payment"}.')
        return redirect(self.get_success_url())

    def form_invalid(self, form, team_formset, equipment_formset):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                team_formset=team_formset,
                equipment_formset=equipment_formset
            )
        )

class SurgeryUpdateView(LoginRequiredMixin, UpdateView):
    model = Surgery
    form_class = SurgeryForm
    template_name = 'theatre/surgery_form.html'
    success_url = reverse_lazy('theatre:surgery_list')


class SurgeryDeleteView(LoginRequiredMixin, DeleteView):
    model = Surgery
    template_name = 'theatre/surgery_confirm_delete.html'
    success_url = reverse_lazy('theatre:surgery_list')


# Surgical Equipment Views
class SurgicalEquipmentListView(LoginRequiredMixin, ListView):
    model = SurgicalEquipment
    template_name = 'theatre/equipment_list.html'
    context_object_name = 'object_list'

class SurgicalEquipmentDetailView(LoginRequiredMixin, DetailView):
    model = SurgicalEquipment
    template_name = 'theatre/equipment_detail.html'

class SurgicalEquipmentCreateView(LoginRequiredMixin, CreateView):
    model = SurgicalEquipment
    form_class = SurgicalEquipmentForm
    template_name = 'theatre/equipment_form.html'
    success_url = reverse_lazy('theatre:equipment_list')

class SurgicalEquipmentUpdateView(LoginRequiredMixin, UpdateView):
    model = SurgicalEquipment
    form_class = SurgicalEquipmentForm
    template_name = 'theatre/equipment_form.html'
    success_url = reverse_lazy('theatre:equipment_list')

class SurgicalEquipmentDeleteView(LoginRequiredMixin, DeleteView):
    model = SurgicalEquipment
    template_name = 'theatre/equipment_confirm_delete.html'
    success_url = reverse_lazy('theatre:equipment_list')


# Surgical Team Management Views
class SurgicalTeamListView(LoginRequiredMixin, ListView):
    model = SurgicalTeam
    template_name = 'theatre/team_list.html'
    context_object_name = 'teams'
    paginate_by = 20

    def get_queryset(self):
        queryset = SurgicalTeam.objects.select_related('surgery', 'staff', 'surgery__patient').order_by('-surgery__scheduled_date')

        # Add search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(staff__first_name__icontains=search_query) |
                Q(staff__last_name__icontains=search_query) |
                Q(surgery__patient__first_name__icontains=search_query) |
                Q(surgery__patient__last_name__icontains=search_query) |
                Q(role__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class SurgicalTeamDetailView(LoginRequiredMixin, DetailView):
    model = SurgicalTeam
    template_name = 'theatre/team_detail.html'


class SurgicalTeamCreateView(LoginRequiredMixin, CreateView):
    model = SurgicalTeam
    fields = ['surgery', 'staff', 'role', 'usage_notes']
    template_name = 'theatre/team_form.html'
    success_url = reverse_lazy('theatre:team_list')

    def form_valid(self, form):
        messages.success(self.request, 'Surgical team member added successfully.')
        return super().form_valid(form)


class SurgicalTeamUpdateView(LoginRequiredMixin, UpdateView):
    model = SurgicalTeam
    fields = ['surgery', 'staff', 'role', 'usage_notes']
    template_name = 'theatre/team_form.html'
    success_url = reverse_lazy('theatre:team_list')

    def form_valid(self, form):
        messages.success(self.request, 'Surgical team member updated successfully.')
        return super().form_valid(form)


class SurgicalTeamDeleteView(LoginRequiredMixin, DeleteView):
    model = SurgicalTeam
    template_name = 'theatre/team_confirm_delete.html'
    success_url = reverse_lazy('theatre:team_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Surgical team member deleted successfully.')
        return super().delete(request, *args, **kwargs)


class TheatreDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'theatre/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Get today's surgeries
        context['todays_surgeries'] = Surgery.objects.filter(
            scheduled_date__date=today
        ).order_by('scheduled_date')
        
        # Get upcoming surgeries (next 7 days)
        context['upcoming_surgeries'] = Surgery.objects.filter(
            scheduled_date__date__gt=today,
            scheduled_date__date__lte=today + timezone.timedelta(days=7)
        ).order_by('scheduled_date')
        
        # Get theatre availability
        context['available_theatres'] = OperationTheatre.objects.filter(is_available=True).count()
        context['total_theatres'] = OperationTheatre.objects.count()
        
        # Get surgery statistics
        context['total_surgeries'] = Surgery.objects.count()
        context['completed_surgeries'] = Surgery.objects.filter(status='completed').count()
        context['scheduled_surgeries'] = Surgery.objects.filter(status='scheduled').count()
        context['cancelled_surgeries'] = Surgery.objects.filter(status='cancelled').count()
        
        # Get equipment statistics
        context['total_equipment'] = SurgicalEquipment.objects.count()
        context['available_equipment'] = SurgicalEquipment.objects.filter(is_available=True).count()
        context['maintenance_due'] = SurgicalEquipment.objects.filter(
            next_maintenance_date__lte=today
        ).count()
        
        return context


# Equipment Maintenance and Calibration Views
class EquipmentMaintenanceView(LoginRequiredMixin, ListView):
    model = SurgicalEquipment
    template_name = 'theatre/equipment_maintenance.html'
    context_object_name = 'equipment_due'

    def get_queryset(self):
        today = timezone.now().date()
        # Filter for equipment due for maintenance or calibration
        # This is a simplified example; a real-world scenario might involve more complex logic
        # and potentially a custom manager or method on the model.
        return SurgicalEquipment.objects.filter(
            Q(next_maintenance_date__lte=today) | Q(last_calibration_date__lte=today)
        ).order_by('next_maintenance_date', 'last_calibration_date')


# Reporting Views
class SurgeryReportView(LoginRequiredMixin, TemplateView):
    template_name = 'theatre/surgery_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Total surgeries by status
        context['surgeries_by_status'] = Surgery.objects.values('status').annotate(count=Count('id'))

        # Surgeries by type
        context['surgeries_by_type'] = Surgery.objects.values('surgery_type__name').annotate(count=Count('id'))

        # Surgeries by surgeon
        context['surgeries_by_surgeon'] = Surgery.objects.values('primary_surgeon__first_name', 'primary_surgeon__last_name').annotate(count=Count('id'))

        # Complications (simple count for now)
        context['complications_count'] = PostOperativeNote.objects.exclude(complications__isnull=True).exclude(complications__exact='').count()

        return context


@login_required
def theatre_statistics_report(request):
    """Comprehensive theatre statistics and reporting"""
    from django.db.models import Q, Sum, Count, Avg
    from datetime import datetime, timedelta
    from decimal import Decimal

    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    surgery_type_id = request.GET.get('surgery_type')
    theatre_id = request.GET.get('theatre')
    status = request.GET.get('status')
    surgeon_id = request.GET.get('surgeon')

    # Default date range (last 30 days)
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Base queryset for surgeries
    surgeries = Surgery.objects.filter(
        scheduled_date__date__gte=start_date,
        scheduled_date__date__lte=end_date
    ).select_related('patient', 'surgery_type', 'theatre', 'primary_surgeon', 'anesthetist')

    # Apply filters
    if surgery_type_id:
        surgeries = surgeries.filter(surgery_type_id=surgery_type_id)

    if theatre_id:
        surgeries = surgeries.filter(theatre_id=theatre_id)

    if status:
        surgeries = surgeries.filter(status=status)

    if surgeon_id:
        surgeries = surgeries.filter(primary_surgeon_id=surgeon_id)

    # Surgeries by theatre
    theatre_stats = surgeries.values(
        'theatre__name',
        'theatre__id'
    ).annotate(
        total_surgeries=Count('id'),
        completed_surgeries=Count('id', filter=Q(status='completed')),
        cancelled_surgeries=Count('id', filter=Q(status='cancelled')),
        avg_duration=Avg('expected_duration'),
        unique_patients=Count('patient', distinct=True),
        unique_surgeons=Count('primary_surgeon', distinct=True)
    ).order_by('-total_surgeries')

    # Top surgery types by volume
    top_surgery_types = surgeries.values(
        'surgery_type__name',
        'surgery_type__id'
    ).annotate(
        total_surgeries=Count('id'),
        completed_surgeries=Count('id', filter=Q(status='completed')),
        avg_duration=Avg('expected_duration'),
        unique_patients=Count('patient', distinct=True)
    ).order_by('-total_surgeries')[:10]

    # Status distribution
    status_stats = surgeries.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # Daily surgery volume trend
    daily_stats = surgeries.extra(
        select={'day': 'DATE(scheduled_date)'}
    ).values('day').annotate(
        daily_surgeries=Count('id'),
        daily_completed=Count('id', filter=Q(status='completed'))
    ).order_by('day')

    # Top surgeons
    top_surgeons = surgeries.filter(
        primary_surgeon__isnull=False
    ).values(
        'primary_surgeon__first_name',
        'primary_surgeon__last_name',
        'primary_surgeon__id'
    ).annotate(
        total_surgeries=Count('id'),
        completed_surgeries=Count('id', filter=Q(status='completed')),
        unique_patients=Count('patient', distinct=True),
        avg_duration=Avg('expected_duration')
    ).order_by('-total_surgeries')[:10]

    # Theatre utilization
    theatre_utilization = surgeries.values(
        'theatre__name',
        'theatre__id'
    ).annotate(
        scheduled_hours=Sum('expected_duration'),
        total_surgeries=Count('id')
    ).order_by('-scheduled_hours')

    # Overall statistics
    overall_stats = surgeries.aggregate(
        total_surgeries=Count('id'),
        completed_surgeries=Count('id', filter=Q(status='completed')),
        cancelled_surgeries=Count('id', filter=Q(status='cancelled')),
        in_progress_surgeries=Count('id', filter=Q(status='in_progress')),
        scheduled_surgeries=Count('id', filter=Q(status='scheduled')),
        avg_duration=Avg('expected_duration'),
        unique_patients=Count('patient', distinct=True),
        unique_surgeons=Count('primary_surgeon', distinct=True),
        unique_theatres=Count('theatre', distinct=True)
    )

    # Success rate (completed vs total)
    total_surgeries = overall_stats['total_surgeries'] or 0
    completed_surgeries = overall_stats['completed_surgeries'] or 0
    success_rate = (completed_surgeries / total_surgeries * 100) if total_surgeries > 0 else 0

    # Cancellation rate
    cancelled_surgeries = overall_stats['cancelled_surgeries'] or 0
    cancellation_rate = (cancelled_surgeries / total_surgeries * 100) if total_surgeries > 0 else 0

    # Complications count (from post-operative notes)
    complications_count = PostOperativeNote.objects.filter(
        surgery__in=surgeries,
        complications__isnull=False
    ).exclude(complications__exact='').count()

    # Get filter options
    surgery_types = SurgeryType.objects.all().order_by('name')
    theatres = OperationTheatre.objects.filter(is_available=True).order_by('name')
    surgeons = CustomUser.objects.filter(
        profile__specialization__icontains='surgeon'
    ).order_by('first_name', 'last_name')

    context = {
        'title': 'Theatre Statistics and Reports',
        'start_date': start_date,
        'end_date': end_date,
        'theatre_stats': theatre_stats,
        'top_surgery_types': top_surgery_types,
        'top_surgeons': top_surgeons,
        'theatre_utilization': theatre_utilization,
        'status_stats': status_stats,
        'daily_stats': daily_stats,
        'overall_stats': overall_stats,
        'success_rate': success_rate,
        'cancellation_rate': cancellation_rate,
        'complications_count': complications_count,
        'surgery_types': surgery_types,
        'theatres': theatres,
        'surgeons': surgeons,
        'selected_surgery_type': surgery_type_id,
        'selected_theatre': theatre_id,
        'selected_status': status,
        'selected_surgeon': surgeon_id,
    }

    return render(request, 'theatre/reports/theatre_statistics.html', context)


# Theatre Dashboard View
@login_required
def create_prescription_for_theatre(request, surgery_id):
    """Create a prescription for a theatre patient"""
    from .models import Surgery
    surgery = get_object_or_404(Surgery, id=surgery_id)
    
    if request.method == 'POST':
        prescription_form = MedicalModulePrescriptionForm(request.POST)
        formset = PrescriptionItemFormSet(request.POST)
        
        if prescription_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Create the prescription
                    diagnosis = prescription_form.cleaned_data['diagnosis']
                    notes = prescription_form.cleaned_data['notes']
                    prescription_type = prescription_form.cleaned_data['prescription_type']
                    
                    prescription = Prescription.objects.create(
                        patient=surgery.patient,
                        doctor=request.user,
                        diagnosis=diagnosis,
                        notes=notes,
                        prescription_type=prescription_type
                    )
                    
                    # Add prescription items
                    for form in formset.cleaned_data:
                        if form and not form.get('DELETE', False):
                            medication = form['medication']
                            dosage = form['dosage']
                            frequency = form['frequency']
                            duration = form['duration']
                            quantity = form['quantity']
                            instructions = form.get('instructions', '')
                            
                            PrescriptionItem.objects.create(
                                prescription=prescription,
                                medication=medication,
                                dosage=dosage,
                                frequency=frequency,
                                duration=duration,
                                quantity=quantity,
                                instructions=instructions
                            )
                    
                    messages.success(request, 'Prescription created successfully!')
                    return redirect('theatre:surgery_detail', pk=surgery.id)
                    
            except Exception as e:
                messages.error(request, f'Error creating prescription: {str(e)}')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        prescription_form = MedicalModulePrescriptionForm()
        formset = PrescriptionItemFormSet()
    
    context = {
        'surgery': surgery,
        'prescription_form': prescription_form,
        'formset': formset,
        'title': 'Create Prescription'
    }
    return render(request, 'theatre/create_prescription.html', context)