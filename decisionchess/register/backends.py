from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

User = get_user_model()

class CustomAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):

        UserModel = get_user_model()

        # Check if the input is an email address
        if '@' in username:
            kwargs = {'email': username}
        else:
            kwargs = {'username': username}

        try:
            user = UserModel.objects.get(**kwargs)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password) and not user.bot_account:
            return user

        if user and user.bot_account:
            # Prevent login for bot users
            raise PermissionDenied("Unauthorized")
