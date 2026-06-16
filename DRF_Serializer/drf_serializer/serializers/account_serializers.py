from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from drf_serializer.models import Account
from drf_serializer.fields import MoneyField, MaskedCardField
from drf_serializer.serializers.user_serializer import UserSerializer


class AccountSerializer(serializers.ModelSerializer):
    balance_bdt = MoneyField(source="balance", read_only=True)
    card_display = MaskedCardField(source="card_number", read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "account_number",
            "account_type",
            "balance",
            "balance_bdt",
            "card_number",
            "card_display",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_account_number(self, value):
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                _("Account number must be at least 5 characters.")
            )
        return value.strip()


class AccountListSerializer(serializers.ListSerializer):
    child = AccountSerializer()

    def create(self, validated_data):
        accounts = [Account(**item) for item in validated_data]
        return Account.objects.bulk_create(accounts)

    def update(self, instance_list, validated_data):
        ret = []
        for instance, data in zip(instance_list, validated_data):
            for attr, value in data.items():
                setattr(instance, attr, value)
            instance.save()
            ret.append(instance)
        return ret


class AccountBulkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = "__all__"
        list_serializer_class = AccountListSerializer


class AccountDetailSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source="user", read_only=True)
    balance_bdt = MoneyField(source="balance", read_only=True)
    card_display = MaskedCardField(source="card_number", read_only=True)
    transaction_count = serializers.SerializerMethodField()
    last_transaction_amount = serializers.SerializerMethodField()
    account_summary = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id",
            "account_number",
            "account_type",
            "balance",
            "balance_bdt",
            "card_number",
            "card_display",
            "is_active",
            "created_at",
            "user_details",
            "transaction_count",
            "last_transaction_amount",
            "account_summary",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "balance",
        ]

    def get_transaction_count(self, obj):
        return obj.transactions.count()

    def get_last_transaction_amount(self, obj):
        last_txn = obj.transactions.order_by("-timestamp").first()
        if last_txn:
            return float(last_txn.amount)
        return None

    def get_account_summary(self, obj):
        return (
            f"{obj.get_account_type_display()} account "
            f"#{obj.account_number} \u2014 Balance: ${float(obj.balance):,.2f} "
            f"({obj.transactions.count()} transactions)"
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["meta"] = {
            "type": "account_detail",
            "version": "1.0",
        }
        return data
