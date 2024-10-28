# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils.html import escape, mark_safe
from .redis_helpers import RedisHelper
import json
import uuid
import time
import random

class ChatConsumer(AsyncWebsocketConsumer):
    MESSAGE_LIMIT = 5
    TIME_WINDOW = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_counter = {}
        self.last_message_time = {}

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"
        self.redis_helper = RedisHelper(self.channel_layer)

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
		
        user = await self.get_user()
        guest_id = self.scope.get("session", {}).get("guest_uuid")
        is_member = await self.is_user_game_member(str(user.id) if user and user.is_authenticated else guest_id, self.room_name)
        
        if (is_member and not "spectate" in self.room_name) or "spectate" in self.room_name:
            if user and user.is_authenticated:
                username = user.username
                stored_id = username
            elif "spectate" not in self.room_name:
                username = "Anonymous"
                stored_id = guest_id
            else:
                username = await self.generate_unique_anonymous_username()
                stored_id = guest_id
            
            await self.redis_helper.group_add_user(self.room_group_name, stored_id, username)

            if "spectate" not in self.room_name:
                content = {
                    'type': 'chat.message',
                    'message': {
                        'log': 'connect',
                        'user': username,
                        'text': 'You are connected to the chat room.'
                    }
                }
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    content
                )
                await self.channel_layer.group_send(
                    self.room_group_name + "-spectate",
                    content
                )
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
            game_id = room_name.split("-spectate")[0]
            game = ActiveGames.objects.get(active_game_id=game_id)
            return user_id in (str(game.white_id), str(game.black_id))
        except ActiveGames.DoesNotExist:
            return False

    async def disconnect(self, close_code):
        user = await self.get_user()
        guest_id = self.scope.get("session", {}).get("guest_uuid")
        
        key = user.username if user and user.is_authenticated else guest_id
        username = await self.redis_helper.get_username_by_key(self.room_group_name, key)
        await self.redis_helper.group_discard_user(self.room_group_name, key)
        
        if "spectate" not in self.room_name:
            message = {
                "log": "disconnect",
                "user": username,
                "text": "User has left the chat."
            }
            content = {
                'type': 'chat.message',
                'message': message
            }
            await self.channel_layer.group_send(
                self.room_group_name,
                content
            )
            await self.channel_layer.group_send(
                self.room_group_name + "spectate",
                content
            )

        await self.channel_layer.group_discard(
            self.room_group_name,
			self.channel_name
		)

    async def generate_unique_anonymous_username(self):
        increment = 0
        while True:
            random_number = random.randint(1 + increment, 9999 + increment)
            username = f"Anon-{random_number}"
            existing_users = await self.redis_helper.group_users(self.room_group_name)
            if username not in existing_users.values():
                return username
            increment += 1000

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
        
        user = await self.get_user()
        user_id = guest_id = user.id if user and user.is_authenticated else self.scope.get("session", {}).get("guest_uuid")
        key = user.username if user and user.is_authenticated else guest_id
        username = await self.redis_helper.get_username_by_key(self.room_group_name, key)

        color = message.get('color')
        if username == "Anonymous":
            if "spectate" not in self.room_name:
                message["sender"] = color
        else:
            message["sender"] = username

        if 'log' in message: # TODO restrict log types
            # Process the message without rate-limiting checks
            # Maybe only allow expected logs
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message',
                    'message': message
                }
            )
            return

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
        if "spectate" not in self.room_name and message["end_state"] == '' and message.get('log') is None:
            game_uuid = uuid.UUID(self.room_name)
            message["text"] = escape(message["text"])
            message["sender"] = escape(message["sender"])
            sanitized_sender = mark_safe(message["sender"])
            sanitized_text = mark_safe(message["text"])
            await self.save_active_chat_message(game_uuid, color, user_id, sanitized_sender, sanitized_text)

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

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'game_updates'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_update(self, event):
        update_data = event['data']
        await self.send(text_data=json.dumps(update_data))

class ChallengeConsumer(AsyncWebsocketConsumer):
    MESSAGE_LIMIT = 5
    TIME_WINDOW = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_counter = {}
        self.last_message_time = {}
    
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"challenge_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
		
        user = await self.get_user()
        guest_id = self.scope.get("session", {}).get("guest_uuid")
        is_member, is_challenger = await self.is_user_challenge_member(str(user.id) if user and user.is_authenticated else guest_id, self.room_name)
        
        if is_member:
            content = {
                'type': 'chat.message',
                'message': {
                    'log': 'connect',
                    'user': user.username if user and user.is_authenticated else "Anonymous",
                    'is_challenger': is_challenger,
                    'text': 'You are connected to the chat room.'
                }
            }
            
            await self.channel_layer.group_send(
                self.room_group_name,
                content
            )
        else:
            await self.close()
			
    @database_sync_to_async
    def get_user(self):
        user_id = self.scope.get("session", {}).get("_auth_user_id")
        User = get_user_model()
        return User.objects.get(id=user_id) if user_id else None
    
    @database_sync_to_async
    def is_user_challenge_member(self, user_id, room_name):
        from .models import Challenge # Lazy import to run app
        try:
            challenge_id = room_name
            challenge = Challenge.objects.get(challenge_id=challenge_id)
            is_member = user_id in (str(challenge.white_id), str(challenge.black_id))
            is_challenger = False
            if is_member:
                challenger_id = challenge.white_id if challenge.initiator_color == "white" else challenge.black_id
                if str(challenger_id) == user_id:
                    is_challenger = True
            return is_member, is_challenger
        except Challenge.DoesNotExist:
            return False, False

    async def disconnect(self, close_code):
        user = await self.get_user()
        username = user.username if user and user.is_authenticated else "Anonymous"
        user_id = guest_id = user.id if user and user.is_authenticated else self.scope.get("session", {}).get("guest_uuid")
        is_challenger, _ = await self.is_challenger_and_open(str(user_id), self.room_name)

        message = {
            "log": "disconnect",
            "user": username,
            "is_challenger": is_challenger,
            "text": "User has left the chat."
        }
        content = {
            'type': 'chat.message',
            'message': message
        }
        await self.channel_layer.group_send(
            self.room_group_name,
            content
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
        
        user = await self.get_user()
        user_id = guest_id = user.id if user and user.is_authenticated else self.scope.get("session", {}).get("guest_uuid")
        username = user.username if user and user.is_authenticated else "Anonymous"
        is_challenger, is_open = await self.is_challenger_and_open(str(user_id), self.room_name)
        if not is_open:
            return
        message['is_challenger'] = is_challenger

        if 'log' in message:
            return

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

        # Continue chat after challenge ends but don't save
        if is_open:
            challenge_uuid = uuid.UUID(self.room_name)
            message["text"] = escape(message["text"])
            sanitized_text = mark_safe(message["text"])
            await self.save_active_chat_message(challenge_uuid, is_challenger, user_id, username, sanitized_text)

        self.update_rate_limit_counters(user_id)

    @database_sync_to_async
    def is_challenger_and_open(self, user_id, room_name):
        from .models import Challenge # Lazy import to run app
        try:
            challenge_id = room_name
            challenge = Challenge.objects.get(challenge_id=challenge_id)
            is_challenger = False
            challenger_id = challenge.white_id if challenge.initiator_color == "white" else challenge.black_id
            if str(challenger_id) == user_id:
                is_challenger = True
            if challenge.challenge_accepted is not None:
                return is_challenger, False
            return is_challenger, True
        except Challenge.DoesNotExist:
            return None, False

    @database_sync_to_async
    def save_active_chat_message(self, challenge_uuid, is_challenger, sender_id, username, text):
        from .models import ChallengeMessages # Lazy import to run app
        chat_message = ChallengeMessages(
            challenge_id=challenge_uuid, 
            sender_is_initiator=is_challenger, 
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

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = await self.get_user()
        username = user.username if user and user.is_authenticated else None
        if username is not None:
            self.username = username
            self.room_group_name = f"notifications_{self.username}"
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    @database_sync_to_async
    def get_user(self):
        user_id = self.scope.get("session", {}).get("_auth_user_id")
        User = get_user_model()
        return User.objects.get(id=user_id) if user_id else None

    async def send_update(self, event):
        update_data = event['data']
        await self.send(text_data=json.dumps(update_data))