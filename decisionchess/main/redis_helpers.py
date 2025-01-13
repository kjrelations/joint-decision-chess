import redis.asyncio as aioredis
from django.conf import settings
import json

class RedisHelper:
    def __init__(self, channel_layer):
        self.channel_layer = channel_layer
        self.redis_client = aioredis.from_url(settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0])

    async def group_add_user(self, group, key, value):
        """Store a key-value pair (guest_id: generated_username or username: username) in a Redis hash for a given group."""
        existing = await self.redis_client.hget(f"group:{group}:users", key) 
        set_value = {"name": value, "count": json.loads(existing.decode('utf-8'))["count"] + 1} if existing is not None else {"name": value, "count": 1}
        await self.redis_client.hset(f"group:{group}:users", key, json.dumps(set_value))

    async def group_discard_user(self, group, key):
        """Remove the key (guest_id or username) from the Redis hash for the group."""
        existing = await self.redis_client.hget(f"group:{group}:users", key) 
        if existing is not None:
            existing = json.loads(existing.decode('utf-8'))
            if existing["count"] == 1:
                await self.redis_client.hdel(f"group:{group}:users", key)
            else:
                await self.redis_client.hset(f"group:{group}:users", key, json.dumps({"name": existing["name"], "count": existing["count"] - 1}))

    async def group_users(self, group):
        """Get all key-value pairs (guest_id: generated_username or username: username) for the group."""
        users = await self.redis_client.hgetall(f"group:{group}:users")
        return {key.decode('utf-8'): json.loads(value.decode('utf-8')) for key, value in users.items()}
    
    async def get_username_by_key(self, group, key):
        """Retrieve the username from Redis for a given key."""
        value = await self.redis_client.hget(f"group:{group}:users", key) 
        return json.loads(value.decode('utf-8'))["name"] if value else None