from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ChessLobby, User, ActiveGames

@receiver(post_save, sender=ChessLobby)
def notify_update_on_save(sender, instance, **kwargs):
    channel_layer = get_channel_layer()

    white_user = User.objects.filter(id=instance.white_id).first()
    white_username = white_user.username if white_user else 'Anon'
    
    black_user = User.objects.filter(id=instance.black_id).first()
    black_username = black_user.username if black_user else 'Anon'
    
    active_game = ActiveGames.objects.filter(active_game_id=instance.lobby_id).first()
    
    start_time = str(active_game.start_time) if active_game else None
    is_ready = start_time is None and instance.initiator_connected and instance.opponent_connected

    multiplayer = not instance.computer_game and not instance.solo_game and not instance.private

    async_to_sync(channel_layer.group_send)(
        'game_updates',
        {
            'type': 'send_update',
            'data': {
                'action': 'save',
                'id': str(instance.lobby_id),
                'white_username': white_username,
                'black_username': black_username,
                'gametype': instance.gametype,
                'start_time': start_time,
                'new_multiplayer': is_ready and multiplayer
            }
        }
    )

@receiver(post_delete, sender=ChessLobby)
def notify_update_on_delete(sender, instance, **kwargs):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        'game_updates',
        {
            'type': 'send_update',
            'data': {
                'action': 'delete',
                'id': str(instance.lobby_id)
            }
        }
    )