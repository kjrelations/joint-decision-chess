from django.core.management.base import BaseCommand
from main.models import User
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, module="django.db.models.fields")

class Command(BaseCommand):
    help = 'Delete two week old inactive users from the database'

    def handle(self, *args, **options):

        expired = datetime.now() - timedelta(weeks=2)

        users_to_delete = User.objects.filter(
            date_joined__lt=expired,
            is_active=False
            )

        for user in users_to_delete:
            user.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted user: {user.username}'))