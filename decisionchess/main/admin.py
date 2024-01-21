from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.sessions.models import Session
from .models import User
import json

class SessionAdmin(admin.ModelAdmin):
    def email(self, obj):
        session_user = obj.get_decoded().get('_auth_user_id')
        user = User.objects.get(pk=session_user)
        return user.email
    def user_id(self, obj):
        session_user = obj.get_decoded().get('_auth_user_id')
        if session_user is None:
            session_user = obj.get_decoded().get('guest_uuid')
        return session_user
    def _session_data(self, obj):
        return json.dumps(obj.get_decoded(), indent=2)
    _session_data.allow_tags = True
    list_display = ['email', 'user_id', '_session_data', 'expire_date', 'session_key']
    readonly_fields = ['_session_data']

admin.site.register(User, UserAdmin)
admin.site.register(Session, SessionAdmin)