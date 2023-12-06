# Admin script to quickly create bot rows, run from main directory with python -m register.bot_register
import os
import django

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decisionchess.settings")

# Configure Django settings
django.setup()

from main.models import User, BotInformation

bot_config = ""
bot_name = ""
dummy_email = ""
bot_pass = ""
user = User.objects.create_user(username=bot_name, email=dummy_email, password=bot_pass, bot_account=True)

botInfo = BotInformation(
    bot_id = user.id,
    config = bot_config
)