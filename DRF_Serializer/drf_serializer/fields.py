from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

BDT_RATE = 120.0


class MoneyField(serializers.DecimalField):
    def __init__(self, bdt_rate=BDT_RATE, **kwargs):
        self.bdt_rate = bdt_rate
        kwargs.setdefault("max_digits", 14)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(**kwargs)

    def to_representation(self, value):
        if value is None:
            return None
        value = super().to_representation(value)
        from decimal import Decimal
        bdt_value = Decimal(str(value)) * Decimal(str(self.bdt_rate))
        return float(bdt_value.quantize(Decimal("0.01")))

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        from decimal import Decimal
        usd_value = value / Decimal(str(self.bdt_rate))
        return usd_value.quantize(Decimal("0.01"))


class MaskedCardField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 16)
        kwargs.setdefault("min_length", 13)
        super().__init__(**kwargs)

    def to_representation(self, value):
        if not value:
            return value
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 4:
            return value
        return f"**** **** **** {digits[-4:]}"

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        digits = "".join(ch for ch in data if ch.isdigit())
        if len(digits) < 13:
            raise serializers.ValidationError(
                _("Card number must contain at least 13 digits.")
            )
        if len(digits) > 16:
            raise serializers.ValidationError(
                _("Card number must contain at most 16 digits.")
            )
        try:
            int(digits)
        except ValueError:
            raise serializers.ValidationError(
                _("Card number must contain only digits.")
            )
        return digits
