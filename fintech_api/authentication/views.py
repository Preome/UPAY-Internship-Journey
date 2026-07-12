from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenRefreshView

from .models import BlacklistedToken, ActiveSession
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    CustomTokenObtainPairSerializer,
    TokenRefreshWithRotationSerializer,
    LogoutSerializer,
    ActiveSessionSerializer,
)
from accounts.permissions import IsAdmin, IsAgent, HasRole


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _get_device_info(request):
    ua = request.META.get('HTTP_USER_AGENT', '')
    return ua[:500] if ua else ''


def _create_session(user, refresh_token, request):
    jti = refresh_token.get('jti')
    return ActiveSession.objects.create(
        user=user,
        jti=jti,
        device=_get_device_info(request),
        ip_address=_get_client_ip(request),
        token_type='refresh',
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        token_serializer = CustomTokenObtainPairSerializer()
        refresh = token_serializer.get_token(user)

        session = _create_session(user, refresh, request)

        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'session': {
                'id': session.id,
                'device': session.device[:50] if session.device else '',
                'ip_address': session.ip_address,
            },
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        login_serializer = LoginSerializer(
            data=request.data,
            context={'request': request},
        )
        if not login_serializer.is_valid():
            return Response(
                login_serializer.errors,
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = login_serializer.validated_data['user']
        token_serializer = CustomTokenObtainPairSerializer()
        refresh = token_serializer.get_token(user)

        session = _create_session(user, refresh, request)

        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'session': {
                'id': session.id,
                'device': session.device[:50] if session.device else '',
                'ip_address': session.ip_address,
            },
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        jti = serializer.validated_data['jti']
        user_id = serializer.validated_data['user_id']

        if int(user_id) != request.user.pk:
            return Response(
                {'error': 'Token does not belong to the authenticated user.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        BlacklistedToken.objects.create(
            jti=jti,
            user=request.user,
            expires_at=timezone.now() + timezone.timedelta(days=1),
        )
        ActiveSession.objects.filter(jti=jti).update(is_active=False)

        return Response({'detail': 'Successfully logged out.'})


class TokenRefreshWithRotationView(TokenRefreshView):
    serializer_class = TokenRefreshWithRotationSerializer
    permission_classes = [AllowAny]


class TokenRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token_str = request.data.get('refresh')
        if not refresh_token_str:
            return Response(
                {'error': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token_str)
        except TokenError:
            return Response(
                {'error': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        jti = token.get('jti')
        user_id = token.get('user_id')

        if not jti or not user_id:
            return Response(
                {'error': 'Invalid token payload.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if int(user_id) != request.user.pk:
            return Response(
                {'error': 'You can only revoke your own tokens.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if BlacklistedToken.is_blacklisted(jti):
            return Response(
                {'error': 'Token already revoked.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        BlacklistedToken.objects.create(
            jti=jti,
            user=request.user,
            expires_at=timezone.now() + timezone.timedelta(days=1),
        )
        ActiveSession.objects.filter(jti=jti).update(is_active=False)

        return Response({'detail': 'Token revoked successfully.'})


class ActiveSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = ActiveSession.objects.filter(
            user=request.user,
            is_active=True,
        )
        serializer = ActiveSessionSerializer(sessions, many=True)
        return Response({'sessions': serializer.data})

    def delete(self, request, session_id=None):
        if session_id:
            session = ActiveSession.objects.filter(
                id=session_id,
                user=request.user,
            ).first()
            if not session:
                return Response(
                    {'error': 'Session not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            BlacklistedToken.objects.get_or_create(
                jti=session.jti,
                defaults={
                    'user': request.user,
                    'expires_at': timezone.now() + timezone.timedelta(days=1),
                },
            )
            session.revoke()
            return Response({'detail': f'Session {session_id} revoked.'})

        sessions = ActiveSession.objects.filter(
            user=request.user,
            is_active=True,
        )
        for session in sessions:
            BlacklistedToken.objects.get_or_create(
                jti=session.jti,
                defaults={
                    'user': request.user,
                    'expires_at': timezone.now() + timezone.timedelta(days=1),
                },
            )
            session.revoke()

        return Response({'detail': 'All sessions revoked.'})
