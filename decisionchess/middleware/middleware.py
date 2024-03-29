from django.conf import settings
import uuid
import logging

# To ensure sessions are created only on first visit on any page for guests
class GuestSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (not hasattr(request, 'user') or not request.user.is_authenticated) \
            and 'guest_uuid' not in request.session:
                # Generate a unique guest UUID
                guest_uuid = uuid.uuid4()
                guest_uuid_str = str(guest_uuid)

                # Create a session for the guest user
                request.session['guest_uuid'] = guest_uuid_str

                # Save the session to ensure it's persisted
                request.session.save()
        else:
            # If user is authenticated after logging in remove guest_uuid
            if 'guest_uuid' in request.session and \
                (hasattr(request, 'user') and request.user.is_authenticated):
                del request.session['guest_uuid']

                request.session.modified = True
                request.session.save()

        response = self.get_response(request)
        return response
    
class ExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = None
        try:
            response = self.get_response(request)
        except Exception as e:
            logging.error(f"Unhandled exception: {e}", exc_info=True)
        return response