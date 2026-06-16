from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from drf_serializer.models import Account, Transaction
from drf_serializer.fields import MoneyField


class TransactionSerializer(serializers.ModelSerializer):
    amount_taka = MoneyField(source="amount", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "amount",
            "amount_taka",
            "transaction_type",
            "description",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                _("Transaction amount must be positive.")
            )
        return value


class UserNestedSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class AccountNestedSerializer(serializers.ModelSerializer):
    user = UserNestedSerializer()
    card_display = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id",
            "account_number",
            "account_type",
            "card_number",
            "card_display",
            "is_active",
            "user",
        ]

    def get_card_display(self, obj):
        if not obj.card_number:
            return None
        return f"**** **** **** {obj.card_number[-4:]}"

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = UserNestedSerializer().create(user_data)
        return Account.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            UserNestedSerializer().update(instance.user, user_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class NestedTransactionSerializer(serializers.ModelSerializer):
    account = AccountNestedSerializer()
    amount_taka = MoneyField(source="amount", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "amount",
            "amount_taka",
            "transaction_type",
            "description",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp", "amount_taka"]

    def create(self, validated_data):
        account_data = validated_data.pop("account")
        account = AccountNestedSerializer().create(account_data)
        return Transaction.objects.create(account=account, **validated_data)

    def update(self, instance, validated_data):
        account_data = validated_data.pop("account", None)
        if account_data:
            AccountNestedSerializer().update(instance.account, account_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class TransactionCreateSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = serializers.ChoiceField(
        choices=["DEPOSIT", "WITHDRAWAL", "TRANSFER", "PAYMENT"]
    )
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate_account_id(self, value):
        if not Account.objects.filter(id=value).exists():
            raise serializers.ValidationError("Account does not exist.")
        return value

    def create(self, validated_data):
        return Transaction.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
