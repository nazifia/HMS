from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from theatre.models import SurgicalEquipment, EquipmentMaintenanceLog
from theatre.forms import EquipmentMaintenanceLogForm
from .views import ReceptionistHROAccessMixin, theatre_access_required


class EquipmentMaintenanceLogListView(
    LoginRequiredMixin, ReceptionistHROAccessMixin, ListView
):
    """View to list all maintenance logs for a specific equipment."""

    model = EquipmentMaintenanceLog
    template_name = "theatre/equipment_maintenance_log_list.html"
    context_object_name = "maintenance_logs"
    paginate_by = 20

    def get_queryset(self):
        equipment_id = self.kwargs.get("equipment_id")
        if equipment_id:
            return (
                EquipmentMaintenanceLog.objects.filter(equipment_id=equipment_id)
                .select_related("equipment", "performed_by")
                .order_by("-scheduled_date")
            )
        return EquipmentMaintenanceLog.objects.select_related(
            "equipment", "performed_by"
        ).order_by("-scheduled_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipment_id = self.kwargs.get("equipment_id")
        if equipment_id:
            context["equipment"] = get_object_or_404(SurgicalEquipment, id=equipment_id)
        return context


class EquipmentMaintenanceLogCreateView(
    LoginRequiredMixin, ReceptionistHROAccessMixin, CreateView
):
    """View to create a new maintenance log for equipment."""

    model = EquipmentMaintenanceLog
    form_class = EquipmentMaintenanceLogForm
    template_name = "theatre/equipment_maintenance_log_form.html"

    def get_initial(self):
        initial = super().get_initial()
        equipment_id = self.kwargs.get("equipment_id")
        if equipment_id:
            initial["equipment"] = get_object_or_404(SurgicalEquipment, id=equipment_id)
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        equipment_id = self.kwargs.get("equipment_id")
        if equipment_id:
            kwargs["equipment"] = get_object_or_404(SurgicalEquipment, id=equipment_id)
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        # Update equipment dates based on maintenance type
        equipment = form.instance.equipment
        if form.instance.status == "completed":
            if form.instance.maintenance_type == "maintenance":
                equipment.last_maintenance_date = form.instance.completed_date
                equipment.next_maintenance_date = form.instance.next_due_date
            elif form.instance.maintenance_type == "calibration":
                equipment.last_calibration_date = form.instance.completed_date

        equipment.save()

        messages.success(
            self.request,
            f"{form.instance.get_maintenance_type_display()} recorded successfully for {equipment.name}.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        equipment_id = self.kwargs.get("equipment_id")
        if equipment_id:
            return reverse_lazy("theatre:equipment_detail", kwargs={"pk": equipment_id})
        return reverse_lazy("theatre:equipment_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipment_id = self.kwargs.get("equipment_id")
        if equipment_id:
            context["equipment"] = get_object_or_404(SurgicalEquipment, id=equipment_id)
        return context


class EquipmentMaintenanceLogUpdateView(
    LoginRequiredMixin, ReceptionistHROAccessMixin, UpdateView
):
    """View to update an existing maintenance log."""

    model = EquipmentMaintenanceLog
    form_class = EquipmentMaintenanceLogForm
    template_name = "theatre/equipment_maintenance_log_form.html"
    pk_url_kwarg = "log_id"

    def form_valid(self, form):
        # Update equipment dates based on maintenance type if status changed to completed
        equipment = form.instance.equipment
        if form.instance.status == "completed" and form.instance.completed_date:
            if form.instance.maintenance_type == "maintenance":
                equipment.last_maintenance_date = form.instance.completed_date
                equipment.next_maintenance_date = form.instance.next_due_date
            elif form.instance.maintenance_type == "calibration":
                equipment.last_calibration_date = form.instance.completed_date

        equipment.save()

        messages.success(
            self.request,
            f"{form.instance.get_maintenance_type_display()} updated successfully.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        equipment_id = self.object.equipment.id
        return reverse_lazy("theatre:equipment_detail", kwargs={"pk": equipment_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["equipment"] = self.object.equipment
        context["is_update"] = True
        return context


@login_required
@theatre_access_required
def equipment_maintenance_calendar(request, equipment_id):
    """View maintenance calendar for equipment."""
    equipment = get_object_or_404(SurgicalEquipment, id=equipment_id)

    # Get upcoming maintenance
    upcoming = EquipmentMaintenanceLog.objects.filter(
        equipment=equipment, scheduled_date__gte=timezone.now().date()
    ).order_by("scheduled_date")

    # Get maintenance history
    history = EquipmentMaintenanceLog.objects.filter(
        equipment=equipment, scheduled_date__lt=timezone.now().date()
    ).order_by("-scheduled_date")

    context = {
        "equipment": equipment,
        "upcoming_maintenance": upcoming,
        "maintenance_history": history,
    }

    return render(request, "theatre/equipment_maintenance_calendar.html", context)
