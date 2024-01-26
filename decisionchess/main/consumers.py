# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils.html import escape, mark_safe
import json
import uuid
import time

class ChatConsumer(AsyncWebsocketConsumer):
    MESSAGE_LIMIT = 5
    TIME_WINDOW = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_counter = {}
        self.last_message_time = {}

    async def connect(self):
        # TODO Can handle spectator names later with a split on "-spectator" in the room name
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
		
        user = await self.get_user()
        guest_id = self.scope.get("session", {}).get("guest_uuid")
        is_member = await self.is_user_game_member(str(user.id) if user and user.is_authenticated else guest_id, self.room_name)
        
        if is_member:
            username = user.username if user and user.is_authenticated else 'Anonymous'
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                'type': 'chat.message',
                'message': {
                    'log': 'connect',
                    'user': username,
                    'text': 'You are connected to the chat room.'
                }
            })
        else:
            await self.close()
			
    @database_sync_to_async
    def get_user(self):
        user_id = self.scope.get("session", {}).get("_auth_user_id")
        User = get_user_model()
        return User.objects.get(id=user_id) if user_id else None
    
    @database_sync_to_async
    def is_user_game_member(self, user_id, room_name):
        from .models import ActiveGames # Lazy import to run app
        try:
            game = ActiveGames.objects.get(active_game_id=room_name)
            return user_id in (str(game.white_id), str(game.black_id))
        except ActiveGames.DoesNotExist:
            return False

    async def disconnect(self, close_code):
        user = await self.get_user()
        if user and user.is_authenticated:
            username = user.username
        else:
            username = "Anonymous"
        message = {
            "log": "disconnect",
            "user": username,
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

    def is_rate_limited(self, user_id):
        current_time = time.time()
        if user_id in self.message_counter:
            if current_time - self.last_message_time[user_id] <= self.TIME_WINDOW:
                return self.message_counter[user_id] >= self.MESSAGE_LIMIT
            else:
                # Reset counters for a new time window
                self.message_counter[user_id] = 0
        return False
    
    def update_rate_limit_counters(self, user_id):
        current_time = time.time()
        if user_id not in self.message_counter:
            self.message_counter[user_id] = 1
        else:
            self.message_counter[user_id] += 1

        self.last_message_time[user_id] = current_time

    async def send_error_message(self, error_message):
        await self.send(text_data=json.dumps({
            'message': {
                'log': 'spam',
                'text': error_message
                }
        }))

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        username = message["sender"]
        color = message["color"]
        if username == "Anonymous":
            message["sender"] = color

        if 'log' in message:
            # Process the message without rate-limiting checks
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message',
                    'message': message
                }
            )
            return

        user = await self.get_user()
        user_id = guest_id = self.scope.get("session", {}).get("guest_uuid") if user is None else user.id
        if self.is_rate_limited(user_id):
            await self.send_error_message("Too many messages within 10 seconds")
            return

        if len(message['text']) > 250:
            await self.send_error_message("Message too long (250max)")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': message
            }
        )

        # Continue chat after game ends but don't save
        # TODO maybe check historic db row DNE instead, this would be slower though even if secure to execute each time
        # Maybe have a chat attribute set for when a game ends via a confirmed jwt token
        if message["end_state"] == '' and message.get('log') is None:
            sender = await self.get_user()
            if username == "Anonymous":
                sender_id = uuid.UUID(self.scope.get("session", {}).get("guest_uuid"))
            else:
                sender_id = sender.id
            game_uuid = uuid.UUID(self.room_name)
            message["text"] = escape(message["text"])
            message["sender"] = escape(message["sender"])
            sanitized_sender = mark_safe(message["sender"])
            sanitized_text = mark_safe(message["text"])
            await self.save_active_chat_message(game_uuid, color, sender_id, sanitized_sender, sanitized_text)

        self.update_rate_limit_counters(user_id)

    @database_sync_to_async
    def save_active_chat_message(self, game_uuid, color, sender_id, username, text):
        from .models import ActiveChatMessages # Lazy import to run app
        chat_message = ActiveChatMessages(
            game_id=game_uuid, 
            sender_color=color, 
            sender=sender_id, 
            sender_username=username, 
            message=text
        )
        chat_message.save()

    async def chat_message(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))