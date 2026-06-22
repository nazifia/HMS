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
    list_display = ("hospital", "plan", "status", "current_period_end", "approved_by")
    list_filter = ("status", "plan")
    readonly_fields = ("approved_at", "approved_by")
    actions = ("approve_subscriptions", "activate_subscriptions", "reject_subscriptions")

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Approval is a platform-superuser power only.
        if not request.user.is_superuser:
            for name in ("approve_subscriptions", "activate_subscriptions", "reject_subscriptions"):
                actions.pop(name, None)
        return actions

    @admin.action(description="Approve → start trial")
    def approve_subscriptions(self, request, queryset):
        n = 0
        for sub in queryset.filter(status="pending"):
            sub.approve(by=request.user)
            n += 1
        self.message_user(request, f"{n} subscription(s) approved (trial started).")

    @admin.action(description="Approve → activate (skip trial)")
    def activate_subscriptions(self, request, queryset):
        n = 0
        for sub in queryset.filter(status="pending"):
            sub.approve(by=request.user, activate=True)
            n += 1
        self.message_user(request, f"{n} subscription(s) activated.")

    @admin.action(description="Reject")
    def reject_subscriptions(self, request, queryset):
        n = 0
        for sub in queryset.filter(status="pending"):
            sub.reject(by=request.user)
            n += 1
        self.message_user(request, f"{n} subscription(s) rejected.")
