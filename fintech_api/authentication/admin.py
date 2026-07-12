from django.contrib import admin
from .models import BlacklistedToken, ActiveSession

@admin.register(BlacklistedToken)
class BlacklistedTokenAdmin(admin.ModelAdmin):
    list_display = ('jti', 'user', 'expires_at', 'blacklisted_at')
    search_fields = ('jti', 'user__email', 'user__username')

@admin.register(ActiveSession)
class ActiveSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'ip_address', 'last_activity', 'is_active')
    list_filter = ('is_active', 'last_activity')
    search_fields = ('user__email', 'user__username', 'device', 'ip_address')
