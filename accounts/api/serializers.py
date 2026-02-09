from rest_framework import serializers
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from ..models import CustomUser, Role, AuditLog, CustomUserProfile
from django.conf import settings
import json

class PermissionSerializer(serializers.ModelSerializer):
    content_type = serializers.SerializerMethodField()
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']
        
    def get_content_type(self, obj):
        return obj.content_type.app_label

class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        source='permissions',
        write_only=True
    )
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'parent', 'permissions', 'permission_ids']
        extra_kwargs = {
            'parent': {'required': False, 'allow_null': True}
        }
        
    def validate_parent(self, value):
        if value and value == self.instance:
            raise serializers.ValidationError("A role cannot be its own parent")
        return value

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUserProfile
        fields = ['phone_number', 'address', 'profile_picture', 
                 'date_of_birth', 'department', 'employee_id',
                 'specialization', 'qualification', 'is_active']
        extra_kwargs = {
            'employee_id': {'required': True}
        }

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=True)
    roles = RoleSerializer(many=True, read_only=True)
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Role.objects.all(),
        source='roles',
        write_only=True
    )
    password = serializers.CharField(write_only=True, required=True, 
                                    style={'input_type': 'password'})
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'phone_number', 'email', 'first_name', 'last_name',
                 'password', 'is_active', 'is_staff', 'is_superuser',
                 'profile', 'roles', 'role_ids']
        extra_kwargs = {
            'password': {'write_only': True},
            'is_superuser': {'read_only': True}
        }
        
    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        role_ids = validated_data.pop('roles', [])
        password = validated_data.pop('password')

        # Extract phone_number for create_user and remove it from validated_data
        phone_number = validated_data.pop('phone_number')

        user = CustomUser.objects.create_user(
            phone_number=phone_number,
            password=password,
            **validated_data
        )

        # Update the auto-created profile (from signal) instead of creating new
        profile = user.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        # Assign roles
        user.roles.set(role_ids)

        return user
        
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        role_ids = validated_data.pop('roles', [])
        password = validated_data.pop('password', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if password:
            instance.set_password(password)
            
        instance.save()
        
        # Update profile
        profile = instance.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()
        
        # Update roles
        instance.roles.set(role_ids)
        
        return instance

class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    target_user = serializers.StringRelatedField()
    details = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'target_user', 'action', 'details', 'timestamp', 'ip_address']
        
    def get_details(self, obj):
        try:
            return json.loads(obj.details)
        except json.JSONDecodeError:
            return obj.details