# Generated by Django 4.2.7 on 2023-11-14 22:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_chesslobby_private'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ActiveChatMessages',
        ),
        migrations.DeleteModel(
            name='ActiveGames',
        ),
        migrations.DeleteModel(
            name='BlogPosts',
        ),
        migrations.DeleteModel(
            name='ChessLobby',
        ),
        migrations.RenameField(
            model_name='chatmessages',
            old_name='gameid',
            new_name='game_id',
        ),
        migrations.RenameField(
            model_name='chatmessages',
            old_name='messageid',
            new_name='message_id',
        ),
        migrations.RenameField(
            model_name='gamehistorytable',
            old_name='blackid',
            new_name='black_id',
        ),
        migrations.RenameField(
            model_name='gamehistorytable',
            old_name='endtime',
            new_name='end_time',
        ),
        migrations.RenameField(
            model_name='gamehistorytable',
            old_name='gameid',
            new_name='historic_game_id',
        ),
        migrations.RenameField(
            model_name='gamehistorytable',
            old_name='starttime',
            new_name='start_time',
        ),
        migrations.RenameField(
            model_name='gamehistorytable',
            old_name='whiteid',
            new_name='white_id',
        ),
    ]
