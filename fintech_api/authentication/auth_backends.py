from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class EmailAuthBackend(BaseBackend):
    """
    Custom authentication backend that allows login with
    email OR username (not just username).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email_or_username = kwargs.get('email') or username
        if email_or_username is None or password is None:
            return None

        try:
            user = User.objects.get(
                Q(email=email_or_username) | Q(username=email_or_username)
            )
        except User.DoesNotExist:
            return None

        if user.check_password(password) and user.is_active:
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
