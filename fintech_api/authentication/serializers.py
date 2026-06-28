from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer as BaseTokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import BlacklistedToken, ActiveSession

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'password2', 'first_name', 'last_name')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not (email and password):
            raise serializers.ValidationError(
                'Both email and password are required.'
            )

        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password,
        )
        if not user:
            raise serializers.ValidationError(
                'Invalid credentials.',
                code='authorization',
            )

        attrs['user'] = user
        return attrs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = 'admin' if user.is_superuser else (
            'staff' if user.is_staff else 'user'
        )
        token['email'] = user.email
        from accounts.models import Account
        account_ids = list(
            Account.objects.filter(user=user).values_list('id', flat=True)
        )
        token['account_ids'] = account_ids
        return token


class TokenRefreshWithRotationSerializer(BaseTokenRefreshSerializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        refresh_token_str = attrs.get('refresh')

        try:
            old_refresh = RefreshToken(refresh_token_str)
        except TokenError as e:
            raise serializers.ValidationError(str(e))

        jti = old_refresh.get('jti')
        user_id = old_refresh.get('user_id')

        if not jti or not user_id:
            raise serializers.ValidationError('Invalid token payload.')

        if BlacklistedToken.is_blacklisted(jti):
            BlacklistedToken.objects.filter(jti=jti).delete()
            ActiveSession.objects.filter(jti=jti).update(is_active=False)
            raise serializers.ValidationError(
                'Token has been revoked. Possible token reuse detected.',
                code='token_blacklisted',
            )

        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            raise serializers.ValidationError('User not found.')

        exp_ts = old_refresh.get('exp')
        if exp_ts:
            expires_at = datetime.fromtimestamp(exp_ts, tz=dt_timezone.utc)
        else:
            expires_at = timezone.now()
        BlacklistedToken.objects.create(
            jti=jti,
            user=user,
            expires_at=expires_at,
        )

        new_refresh = RefreshToken.for_user(user)
        session = ActiveSession.objects.filter(jti=jti, user=user).first()
        if session:
            session.jti = str(new_refresh.get('jti'))
            session.save(update_fields=['jti'])

        return {
            'access': str(new_refresh.access_token),
            'refresh': str(new_refresh),
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        refresh_token_str = attrs.get('refresh')

        try:
            token = RefreshToken(refresh_token_str)
        except TokenError as e:
            raise serializers.ValidationError(f'Invalid token: {str(e)}')

        jti = token.get('jti')
        user_id = token.get('user_id')

        if not jti or not user_id:
            raise serializers.ValidationError('Invalid token payload.')

        if BlacklistedToken.is_blacklisted(jti):
            raise serializers.ValidationError('Token already revoked.')

        attrs['token'] = token
        attrs['jti'] = jti
        attrs['user_id'] = user_id
        return attrs


class ActiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveSession
        fields = ('id', 'jti', 'device', 'ip_address', 'token_type',
                  'is_active', 'last_activity', 'created_at')
        read_only_fields = ('id', 'jti', 'created_at')


class EmptySerializer(serializers.Serializer):
    pass
