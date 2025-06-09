from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from .serializers import (
    UserSerializer, 
    RoleSerializer,
    PermissionSerializer,
    AuditLogSerializer
)
from ..models import CustomUser, Role, AuditLog, CustomUserProfile
import json

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all().select_related('custom_profile')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        # Only show active users by default
        queryset = super().get_queryset()
        if not self.request.query_params.get('show_inactive'):
            queryset = queryset.filter(profile__is_active=True)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            user = serializer.save()
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                target_user=user,
                action='create',
                details=json.dumps({
                    'fields_changed': list(serializer.validated_data.keys())
                }),
                ip_address=self.get_client_ip()
            )
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            # Capture changes before saving
            changes = self._capture_changes(instance, serializer.validated_data)
            user = serializer.save()
            
            if changes:
                AuditLog.objects.create(
                    user=request.user,
                    target_user=user,
                    action='update',
                    details=json.dumps({
                        'changes': changes
                    }),
                    ip_address=self.get_client_ip()
                )
        
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.profile.is_active = False
        user.profile.save()
        
        AuditLog.objects.create(
            user=request.user,
            target_user=user,
            action='deactivate',
            details=json.dumps({}),
            ip_address=self.get_client_ip()
        )
        
        return Response({'status': 'user deactivated'})

    @action(detail=True, methods=['post'])
    def assign_roles(self, request, pk=None):
        user = self.get_object()
        role_ids = request.data.get('role_ids', [])
        
        try:
            roles = Role.objects.filter(id__in=role_ids)
            user.roles.set(roles)
            
            AuditLog.objects.create(
                user=request.user,
                target_user=user,
                action='privilege_change',
                details=json.dumps({
                    'roles_added': [r.name for r in roles],
                    'roles_removed': list(user.roles.exclude(id__in=role_ids).values_list('name', flat=True))
                }),
                ip_address=self.get_client_ip()
            )
            
            return Response({'status': 'roles updated'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _capture_changes(self, instance, validated_data):
        changes = {}
        for field, new_value in validated_data.items():
            old_value = getattr(instance, field, None)
            if old_value != new_value:
                changes[field] = {
                    'old': str(old_value),
                    'new': str(new_value)
                }
        return changes

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def get_queryset(self):
        # Show logs from last 30 days by default
        queryset = AuditLog.objects.all()
        
        # Filter by user if provided
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(target_user_id=user_id)
            
        # Filter by action type
        action_type = self.request.query_params.get('action')
        if action_type:
            queryset = queryset.filter(action=action_type)
            
        # Filter by date range
        days = int(self.request.query_params.get('days', 30))
        cutoff = timezone.now() - timezone.timedelta(days=days)
        queryset = queryset.filter(timestamp__gte=cutoff)
        
        return queryset.order_by('-timestamp')

from django.contrib.auth import login, authenticate
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')

        if not phone_number or not password:
            return Response({'error': 'Please provide both phone number and password'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Authenticate using the custom backend
        user = authenticate(request, username=phone_number, password=password)

        if user:
            if user.is_active:
                login(request, user)  # This creates a session
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'token': token.key,
                    'user_id': user.pk,
                    'phone_number': user.phone_number
                })
            else:
                return Response({'error': 'User account is inactive'},
                                status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'error': 'Invalid Credentials'},
                            status=status.HTTP_401_UNAUTHORIZED)