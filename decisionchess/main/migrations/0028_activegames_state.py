# Generated by Django 4.2.7 on 2023-12-01 00:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0027_user_account_closed_user_email_reference'),
    ]

    operations = [
        migrations.AddField(
            model_name='activegames',
            name='state',
            field=models.TextField(default=''),
        ),
    ]