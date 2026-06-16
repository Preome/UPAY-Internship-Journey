import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from drf_serializer.fields import MoneyField, MaskedCardField


class TestMoneyField:
    def test_to_representation_converts_usd_to_bdt(self):
        field = MoneyField()
        result = field.to_representation(Decimal("100.00"))
        assert result == 12000.0

    def test_to_representation_returns_none_for_none(self):
        field = MoneyField()
        assert field.to_representation(None) is None

    def test_to_internal_value_converts_bdt_to_usd(self):
        field = MoneyField()
        result = field.to_internal_value(12000.0)
        assert result == Decimal("100.00")

    def test_to_internal_value_handles_string_input(self):
        field = MoneyField()
        result = field.to_internal_value("6000")
        assert result == Decimal("50.00")

    def test_custom_rate(self):
        field = MoneyField(bdt_rate=100.0)
        result = field.to_representation(Decimal("50.00"))
        assert result == 5000.0
        result = field.to_internal_value(5000.0)
        assert result == Decimal("50.00")


class TestMaskedCardField:
    def test_to_representation_masks_card_number(self):
        field = MaskedCardField()
        result = field.to_representation("4111111111111234")
        assert result == "**** **** **** 1234"

    def test_to_representation_short_card(self):
        field = MaskedCardField()
        result = field.to_representation("1234")
        assert result == "**** **** **** 1234"

    def test_to_representation_empty(self):
        field = MaskedCardField()
        assert field.to_representation("") == ""

    def test_to_representation_none(self):
        field = MaskedCardField()
        assert field.to_representation(None) is None

    def test_to_internal_value_strips_non_digits(self):
        field = MaskedCardField()
        result = field.to_internal_value("4111-1111-1111-1234")
        assert result == "4111111111111234"

    def test_to_internal_value_rejects_short_card(self):
        field = MaskedCardField()
        import pytest
        with pytest.raises(ValidationError):
            field.to_internal_value("1234")

    def test_to_internal_value_rejects_long_card(self):
        field = MaskedCardField()
        with pytest.raises(ValidationError):
            field.to_internal_value("1" * 20)

    def test_to_internal_value_valid_card(self):
        field = MaskedCardField()
        result = field.to_internal_value("4111111111111111")
        assert result == "4111111111111111"
