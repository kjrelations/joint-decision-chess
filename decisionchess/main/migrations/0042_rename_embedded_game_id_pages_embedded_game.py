# Generated by Django 5.1.1 on 2024-10-03 14:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0041_rename_lesson_id_pages_lesson'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pages',
            old_name='embedded_game_id',
            new_name='embedded_game',
        ),
    ]
