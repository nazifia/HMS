"""Appointment endpoints for the mobile client.

Booking rules (leave, shift hours, double-booking, the NHIA authorization code)
come from `appointments.services`, the same module the booking form uses — the
API must not be a way around them.
"""
from datetime import datetime

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from accounts.models import CustomUser

from ..models import (
    Appointment, AppointmentFollowUp, DoctorLeave, DoctorSchedule,
)
from ..services import (
    BookingError, available_slots, check_doctor_availability,
    resolve_authorization_code, update_status,
)
from .serializers import (
    AppointmentFollowUpSerializer, AppointmentSerializer,
    DoctorLeaveSerializer, DoctorScheduleSerializer,
)

WRITE_PERMISSIONS = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


class AppointmentPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _error(message):
    return Response({'error': str(message)}, status=status.HTTP_400_BAD_REQUEST)


class AppointmentViewSet(viewsets.ModelViewSet):
    """The day's list, plus booking, rescheduling and status changes."""

    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = AppointmentPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('slots',):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = (
            Appointment.objects
            .select_related('patient', 'doctor', 'department', 'consulting_room')
            .order_by('appointment_date')
        )
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('doctor'):
            queryset = queryset.filter(doctor_id=params['doctor'])
        if params.get('patient'):
            queryset = queryset.filter(patient_id=params['patient'])
        if params.get('mine') == 'true':
            queryset = queryset.filter(doctor=self.request.user)
        if params.get('date'):
            queryset = queryset.filter(appointment_date__date=params['date'])
        if params.get('today') == 'true':
            queryset = queryset.filter(
                appointment_date__date=timezone.localtime().date()
            )
        if params.get('upcoming') == 'true':
            queryset = queryset.filter(
                appointment_date__date__gte=timezone.localtime().date()
            )
        if params.get('search'):
            queryset = queryset.filter(
                Q(patient__first_name__icontains=params['search']) |
                Q(patient__last_name__icontains=params['search']) |
                Q(patient__patient_id__icontains=params['search'])
            )
        return queryset

    def _validate_booking(self, serializer, instance=None):
        """Run the shared booking rules over the incoming data."""
        data = serializer.validated_data
        patient = data.get('patient') or (instance and instance.patient)
        doctor = data.get('doctor') or (instance and instance.doctor)
        start = data.get('appointment_date') or (
            instance and instance.appointment_date
        )
        end_time = data.get('end_time', instance.end_time if instance else None)

        local_start = timezone.localtime(start)
        if local_start < timezone.localtime():
            raise BookingError("Appointment cannot be booked in the past.")
        if end_time and end_time <= local_start.time():
            raise BookingError("End time must be after the appointment time.")

        code = resolve_authorization_code(
            patient,
            self.request.data.get('authorization_code', ''),
            instance.authorization_code if instance else None,
        )

        check_doctor_availability(
            doctor,
            local_start.date(),
            local_start.time(),
            end_time,
            exclude_appointment_id=instance.id if instance else None,
        )
        return code

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            code = self._validate_booking(serializer)
        except BookingError as e:
            return _error(e)
        serializer.save(
            created_by=request.user, status='scheduled', authorization_code=code
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            code = self._validate_booking(serializer, instance)
        except BookingError as e:
            return _error(e)
        serializer.save(authorization_code=code)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        appointment = self.get_object()
        try:
            update_status(appointment, request.data.get('status'))
        except BookingError as e:
            return _error(e)
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=False, methods=['get'])
    def slots(self, request):
        """Bookable slots for a doctor on a date.

        `appointment` excludes an appointment from the conflict check, so
        rescheduling does not clash with itself.
        """
        try:
            date = datetime.strptime(request.query_params['date'], '%Y-%m-%d').date()
            doctor = CustomUser.objects.get(id=request.query_params['doctor'])
        except (KeyError, ValueError, CustomUser.DoesNotExist):
            return _error('A valid doctor and date are required.')

        slots, message = available_slots(
            doctor, date, request.query_params.get('appointment')
        )
        return Response({'slots': slots, 'message': message})


class AppointmentFollowUpViewSet(viewsets.ModelViewSet):
    queryset = AppointmentFollowUp.objects.all()
    serializer_class = AppointmentFollowUpSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = AppointmentPagination

    def get_queryset(self):
        queryset = (
            AppointmentFollowUp.objects
            .select_related('appointment__patient')
            .order_by('follow_up_date')
        )
        params = self.request.query_params
        if params.get('appointment'):
            queryset = queryset.filter(appointment_id=params['appointment'])
        if params.get('pending') == 'true':
            queryset = queryset.filter(booked_appointment__isnull=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DoctorScheduleViewSet(viewsets.ModelViewSet):
    """Working hours — what the slot maths is built on."""

    queryset = DoctorSchedule.objects.all()
    serializer_class = DoctorScheduleSerializer
    permission_classes = WRITE_PERMISSIONS

    def get_queryset(self):
        queryset = DoctorSchedule.objects.select_related('doctor').order_by(
            'weekday', 'start_time'
        )
        if self.request.query_params.get('doctor'):
            queryset = queryset.filter(
                doctor_id=self.request.query_params['doctor']
            )
        return queryset


class DoctorLeaveViewSet(viewsets.ModelViewSet):
    queryset = DoctorLeave.objects.all()
    serializer_class = DoctorLeaveSerializer
    permission_classes = WRITE_PERMISSIONS
    pagination_class = AppointmentPagination

    def get_queryset(self):
        queryset = DoctorLeave.objects.select_related('doctor').order_by(
            '-start_date'
        )
        params = self.request.query_params
        if params.get('doctor'):
            queryset = queryset.filter(doctor_id=params['doctor'])
        if params.get('pending') == 'true':
            queryset = queryset.filter(is_approved=False)
        return queryset

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approving leave blocks bookings, so it needs the change right."""
        if not (
            request.user.is_superuser
            or request.user.has_perm('appointments.change_doctorleave')
        ):
            return Response(
                {'error': 'You do not have permission to approve leave.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        leave = self.get_object()
        leave.is_approved = True
        leave.save(update_fields=['is_approved'])
        return Response(DoctorLeaveSerializer(leave).data)
