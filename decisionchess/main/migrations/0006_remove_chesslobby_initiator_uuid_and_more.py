# Generated by Django 4.2.5 on 2023-10-17 20:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_alter_chesslobby_black_uuid_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='chesslobby',
            name='initiator_uuid',
        ),
        migrations.AddField(
            model_name='chesslobby',
            name='initiator_name',
            field=models.CharField(default='Anonymous', max_length=150),
        ),
    ]