import pytest
from django.contrib.auth.models import User
from rest_framework import serializers

from drf_serializer.models import Account


class BrokenSerializer1(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "account_number", "user"]


class FixedSerializer1(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Account
        fields = ["id", "account_number", "user"]


@pytest.mark.django_db
def test_broken_1_nested_without_read_only():
    user = User.objects.create_user(username="fix1")
    account = Account.objects.create(
        user=user,
        account_number="FIX-001",
        card_number="4111111111111111",
    )
    serializer = FixedSerializer1(account)
    assert "user" in serializer.data
    assert serializer.data["user"] == user.username


class BrokenSerializer2(serializers.Serializer):
    name = serializers.CharField()


@pytest.mark.django_db
def test_broken_2_accessing_validated_data_without_is_valid():
    serializer = BrokenSerializer2(data={"name": "test"})
    assert serializer.is_valid()
    assert serializer.validated_data["name"] == "test"


class BrokenSerializer3(serializers.Serializer):
    title = serializers.CharField()
    value = serializers.IntegerField()


@pytest.mark.django_db
def test_broken_3_plain_serializer_save_without_create():
    serializer = BrokenSerializer3(data={"title": "test", "value": 42})
    assert serializer.is_valid()
    with pytest.raises(NotImplementedError):
        serializer.save()


@pytest.mark.django_db
def test_broken_4_validate_override_signature():
    class BadValidateSerializer(serializers.Serializer):
        a = serializers.IntegerField()
        b = serializers.IntegerField()

        def validate(self, data):
            if data["a"] + data["b"] > 100:
                raise serializers.ValidationError("Too large")

    serializer = BadValidateSerializer(data={"a": 10, "b": 20})
    with pytest.raises(AssertionError, match="should return the validated data"):
        serializer.is_valid()


@pytest.mark.django_db
def test_broken_5_bulk_create_without_list_serializer():
    user = User.objects.create_user(username="fix5")

    class FullAccountSerializer(serializers.ModelSerializer):
        class Meta:
            model = Account
            fields = ["id", "account_number", "user"]

    data = [
        {"account_number": "BLK5-01", "user": user.id},
        {"account_number": "BLK5-02", "user": user.id},
    ]
    serializer = FullAccountSerializer(data=data, many=True)
    assert serializer.is_valid(), serializer.errors
    result = serializer.save()
    assert len(result) == 2
    assert Account.objects.filter(account_number="BLK5-01").exists()
    assert Account.objects.filter(account_number="BLK5-02").exists()
