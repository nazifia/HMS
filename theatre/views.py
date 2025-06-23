from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    OperationTheatre, 
    SurgeryType, 
    Surgery, 
    SurgicalTeam, 
    SurgicalEquipment,
    EquipmentUsage,
    SurgerySchedule,
    PostOperativeNote
)
from .forms import (
    OperationTheatreForm, 
    SurgeryTypeForm, 
    SurgeryForm, 
    SurgicalTeamFormSet,
    SurgicalEquipmentForm,
    EquipmentUsageFormSet,
    SurgeryScheduleForm,
    PostOperativeNoteForm,
    SurgeryFilterForm
)

# Operation Theatre Views
class OperationTheatreListView(LoginRequiredMixin, ListView):
    model = OperationTheatre
    template_name = 'theatre/theatre_list.html'
    context_object_name = 'theatres'

class OperationTheatreDetailView(LoginRequiredMixin, DetailView):
    model = OperationTheatre
    template_name = 'theatre/theatre_detail.html'

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

class SurgeryCreateView(LoginRequiredMixin, CreateView):
    model = Surgery
    form_class = SurgeryForm
    template_name = 'theatre/surgery_form.html'
    success_url = reverse_lazy('theatre:surgery_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['team_formset'] = SurgicalTeamFormSet(self.request.POST)
            data['equipment_formset'] = EquipmentUsageFormSet(self.request.POST)
        else:
            data['team_formset'] = SurgicalTeamFormSet()
            data['equipment_formset'] = EquipmentUsageFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        team_formset = context['team_formset']
        equipment_formset = context['equipment_formset']
        with transaction.atomic():
            self.object = form.save()
            if team_formset.is_valid() and equipment_formset.is_valid():
                team_formset.instance = self.object
                team_formset.save()
                equipment_formset.instance = self.object
                equipment_formset.save()
                messages.success(self.request, 'Surgery created successfully.')
                return super().form_valid(form)
            else:
                return self.form_invalid(form)

class SurgeryUpdateView(LoginRequiredMixin, UpdateView):
    model = Surgery
    form_class = SurgeryForm
    template_name = 'theatre/surgery_form.html'
    success_url = reverse_lazy('theatre:surgery_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['team_formset'] = SurgicalTeamFormSet(self.request.POST, instance=self.object)
            data['equipment_formset'] = EquipmentUsageFormSet(self.request.POST, instance=self.object)
        else:
            data['team_formset'] = SurgicalTeamFormSet(instance=self.object)
            data['equipment_formset'] = EquipmentUsageFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        team_formset = context['team_formset']
        equipment_formset = context['equipment_formset']
        with transaction.atomic():
            self.object = form.save()
            if team_formset.is_valid() and equipment_formset.is_valid():
                team_formset.save()
                equipment_formset.save()
                messages.success(self.request, 'Surgery updated successfully.')
                return super().form_valid(form)
            else:
                return self.form_invalid(form)

class SurgeryDeleteView(LoginRequiredMixin, DeleteView):
    model = Surgery
    template_name = 'theatre/surgery_confirm_delete.html'
    success_url = reverse_lazy('theatre:surgery_list')

# Surgical Equipment Views
class SurgicalEquipmentListView(LoginRequiredMixin, ListView):
    model = SurgicalEquipment
    template_name = 'theatre/equipment_list.html'
    context_object_name = 'equipments'

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


# Theatre Dashboard View
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