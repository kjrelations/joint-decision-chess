# Generated by Django 4.2.7 on 2023-12-11 03:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0030_usersettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='chesslobby',
            name='opponent_name',
            field=models.CharField(default='Waiting...', max_length=150),
        ),
    ]