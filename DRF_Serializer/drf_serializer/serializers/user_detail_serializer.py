from rest_framework import serializers
from django.contrib.auth.models import User
from drf_serializer.serializers.account_serializers import AccountSerializer


class UserDetailSerializer(serializers.ModelSerializer):
    accounts = AccountSerializer(many=True, read_only=True)
    account_count = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()
    last_active = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "last_login",
            "account_count",
            "total_balance",
            "last_active",
            "role_label",
            "accounts",
        ]
        read_only_fields = [
            "id",
            "date_joined",
            "last_login",
        ]

    def get_account_count(self, obj):
        return obj.accounts.count()

    def get_total_balance(self, obj):
        total = sum(
            float(acc.balance)
            for acc in obj.accounts.filter(is_active=True)
        )
        return round(total, 2)

    def get_last_active(self, obj):
        if obj.last_login:
            return obj.last_login.isoformat()
        return obj.date_joined.isoformat()

    def get_role_label(self, obj):
        if obj.is_superuser:
            return "Administrator"
        if obj.is_staff:
            return "Staff"
        return "Regular User"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["profile"] = (
            f"{instance.get_full_name() or instance.username} "
            f"| {data['account_count']} account(s) "
            f"| Total: ${data['total_balance']:,.2f}"
        )
        return data

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if "username" in data:
            data["username"] = data["username"].strip().lower()
        return data
