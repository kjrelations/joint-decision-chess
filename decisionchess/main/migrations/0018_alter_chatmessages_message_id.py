# Generated by Django 4.2.7 on 2023-11-14 22:37

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_delete_activechatmessages_delete_activegames_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatmessages',
            name='message_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]