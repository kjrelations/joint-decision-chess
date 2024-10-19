import redis.asyncio as aioredis
from django.conf import settings

class RedisHelper:
    def __init__(self, channel_layer):
        self.channel_layer = channel_layer
        self.redis_client = aioredis.from_url(settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0])

    async def group_add_user(self, group, key, value):
        """Store a key-value pair (guest_id: generated_username or username: username) in a Redis hash for a given group."""
        await self.redis_client.hset(f"group:{group}:users", key, value)

    async def group_discard_user(self, group, key):
        """Remove the key (guest_id or username) from the Redis hash for the group."""
        await self.redis_client.hdel(f"group:{group}:users", key)

    async def group_users(self, group):
        """Get all key-value pairs (guest_id: generated_username or username: username) for the group."""
        users = await self.redis_client.hgetall(f"group:{group}:users")
        return {key.decode('utf-8'): value.decode('utf-8') for key, value in users.items()}
    
    async def get_username_by_key(self, group, key):
        """Retrieve the username from Redis for a given key."""
        value = await self.redis_client.hget(f"group:{group}:users", key) 
        return value.decode('utf-8') if value else None