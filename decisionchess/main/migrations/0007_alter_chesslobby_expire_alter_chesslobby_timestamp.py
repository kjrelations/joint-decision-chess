# Generated by Django 4.2.5 on 2023-10-18 03:54

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_remove_chesslobby_initiator_uuid_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chesslobby',
            name='expire',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='chesslobby',
            name='timestamp',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
