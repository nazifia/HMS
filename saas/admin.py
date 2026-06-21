from django.contrib import admin

from .models import Hospital, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "interval", "max_users", "max_patients", "is_active")


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ("name", "subdomain", "owner", "is_active", "created_at")
    search_fields = ("name", "subdomain")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("hospital", "plan", "status", "current_period_end")
    list_filter = ("status", "plan")
