# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ActiveGames, ActiveChatMessages
import json
import uuid

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
		
        user = await self.get_user()
        if user and user.is_authenticated:
            # TODO Can handle spectator names later with a split on "-spectator" in the room name
            
            is_member = await self.is_user_game_member(str(user.id), self.room_name)
            
            if is_member:
                await self.send(text_data=json.dumps({
                    'message': {
                        'log': 'connect',
                        'text': 'You are connected to the chat room.'
                    }
                }))
            else:
                await self.close()
        else:
            guest_id = self.scope.get("session", {}).get("guest_uuid")
            is_member = await self.is_user_game_member(guest_id, self.room_name)
            if is_member:
                await self.send(text_data=json.dumps({
                    'message': {
                        'log': 'connect',
                        'text': 'You are connected to the chat room.'
                    }
                }))
            else:
                await self.close()
			
    @database_sync_to_async
    def get_user(self):
        user_id = self.scope.get("session", {}).get("_auth_user_id")
        User = get_user_model()
        return User.objects.get(id=user_id) if user_id else None
    
    @database_sync_to_async
    def is_user_game_member(self, user_id, room_name):
        try:
            game = ActiveGames.objects.get(gameid=room_name)
            return user_id in (str(game.whiteid), str(game.blackid))
        except ActiveGames.DoesNotExist:
            return False

    async def disconnect(self, close_code):
        message = {
            "log": "disconnect",
            "text": "User has left the chat."
        }
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': message
            }
        )

        await self.channel_layer.group_discard(
            self.room_group_name,
			self.channel_name
		)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        
        username = message["sender"]
        color = message["color"]
        if username == "Anonymous":
            message["sender"] = color

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': message
            }
        )

        # Continue chat after game ends but don't save
        if message["end_state"] == '':
            sender = await self.get_user()
            if username == "Anonymous":
                sender_id = uuid.UUID(self.scope.get("session", {}).get("guest_uuid"))
            else:
                sender_id = sender.id
            game_uuid = uuid.UUID(self.room_name)
            await self.save_active_chat_message(game_uuid, color, sender_id, message["sender"], message)

    @database_sync_to_async
    def save_active_chat_message(self, game_uuid, color, sender_id, username, message):
        chat_message = ActiveChatMessages(
            gameid=game_uuid, 
            sender_color=color, 
            sender=sender_id, 
            sender_username=username, 
            message=message["text"]
        )
        chat_message.save()

    async def chat_message(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))