import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class BlacklistedToken(models.Model):
    jti = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blacklisted_tokens'
    )
    expires_at = models.DateTimeField()
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blacklisted_tokens'
        indexes = [
            models.Index(fields=['jti']),
            models.Index(fields=['user', 'expires_at']),
        ]

    def __str__(self):
        return f"Blacklisted {self.jti[:12]}... for {self.user.email}"

    @classmethod
    def is_blacklisted(cls, jti):
        return cls.objects.filter(
            jti=jti,
            expires_at__gt=timezone.now()
        ).exists()

    @classmethod
    def clean_expired(cls):
        return cls.objects.filter(expires_at__lte=timezone.now()).delete()


class Role(models.Model):
    ADMIN = 'admin'
    AGENT = 'agent'
    CUSTOMER = 'customer'

    ROLE_CHOICES = (
        (ADMIN, 'Admin'),
        (AGENT, 'Agent'),
        (CUSTOMER, 'Customer'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='role_profile',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CUSTOMER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_roles'

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @classmethod
    def get_role_for_user(cls, user):
        if user.is_superuser:
            return cls.ADMIN
        profile = cls.objects.filter(user=user).first()
        return profile.role if profile else cls.CUSTOMER


class ActiveSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='active_sessions'
    )
    jti = models.CharField(max_length=255, unique=True)
    device = models.CharField(max_length=500, blank=True, default='')
    ip_address = models.CharField(max_length=45, blank=True, default='')
    user_agent = models.TextField(blank=True, default='')
    token_type = models.CharField(max_length=20, default='refresh')
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'active_sessions'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['jti']),
        ]

    def __str__(self):
        device_str = self.device[:30] if self.device else 'Unknown'
        return f"{self.user.email} - {device_str} - {self.ip_address}"

    def revoke(self):
        self.is_active = False
        self.save(update_fields=['is_active'])
