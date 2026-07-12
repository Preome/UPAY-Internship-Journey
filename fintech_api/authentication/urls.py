from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    TokenRefreshWithRotationView,
    TokenRevokeView,
    ActiveSessionsView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('refresh/', TokenRefreshWithRotationView.as_view(), name='auth-refresh'),
    path('revoke/', TokenRevokeView.as_view(), name='auth-revoke'),
    path('sessions/', ActiveSessionsView.as_view(), name='auth-sessions'),
    path('sessions/<int:session_id>/', ActiveSessionsView.as_view(), name='auth-session-detail'),
]
