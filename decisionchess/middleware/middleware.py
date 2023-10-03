import uuid
import hashlib
from django.conf import settings

class GuestSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            if 'guest_uuid' not in request.session:
                # Generate a unique guest UUID
                guest_uuid = uuid.uuid4()
                guest_uuid_str = str(guest_uuid)
                secret_key = settings.SECRET_KEY.encode('utf-8')
                hashed_uuid = hashlib.sha256(secret_key + guest_uuid_str.encode('utf-8')).hexdigest()

                # Create a session for the guest user
                request.session['hashed_guest_uuid'] = hashed_uuid

                # Save the session to ensure it's persisted
                request.session.save()
        else:
            # If user is authenticated after logging in replace guest_uuid with user uuid
            if 'hashed_guest_uuid' in request.session:
                del request.session['hashed_guest_uuid']

                # Generate a hashed UUID for the authenticated user
                user_uuid = str(request.user.id)
                secret_key = settings.SECRET_KEY.encode('utf-8')
                hashed_uuid = hashlib.sha256(secret_key + user_uuid.encode('utf-8')).hexdigest()
                
                # Create a session for the authenticated user
                request.session['hashed_user_uuid'] = hashed_uuid

                request.session.modified = True
                request.session.save()

        response = self.get_response(request)
        return response