# main/context_processors.py
from django.contrib.auth.models import AnonymousUser

def user_context(request):
    user = request.user
    if isinstance(user, AnonymousUser):
        return {'user': None}
    return {'user': user}