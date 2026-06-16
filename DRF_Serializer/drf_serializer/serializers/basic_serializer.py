from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class BasicSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.ChoiceField(choices=["USD", "BDT", "EUR"])
    is_active = serializers.BooleanField(default=True)

    def validate_title(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError(_("Title cannot be blank."))
        if len(stripped) < 3:
            raise serializers.ValidationError(
                _("Title must be at least 3 characters.")
            )
        return stripped

    def validate(self, data):
        if data.get("amount", 0) <= 0:
            raise serializers.ValidationError(
                {"amount": _("Amount must be greater than zero.")}
            )
        if data.get("currency") == "BDT" and data.get("amount", 0) > 1000000:
            raise serializers.ValidationError(
                _("BDT transactions over 1,000,000 require special approval.")
            )
        return data

    def create(self, validated_data):
        return validated_data

    def update(self, instance, validated_data):
        instance.update(validated_data)
        return instance
