# Generated by Django 4.2.7 on 2023-12-01 21:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0028_activegames_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='chesslobby',
            name='opponent_connected',
            field=models.BooleanField(default=False),
        ),
    ]
