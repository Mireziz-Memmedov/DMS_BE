import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]

        self.room_group_name = f"chat_{self.conversation_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()


    async def disconnect(self, close_code):

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )


    async def receive(self, text_data):

        data = json.loads(text_data)

        message_text = data.get("message", "").strip()

        if not message_text:
            return

        message = await self.create_message(
            message_text
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
            }
        )


    async def chat_message(self, event):

        await self.send(
            text_data=json.dumps({
                "message": event["message"]
            })
        )


    @database_sync_to_async
    def create_message(self, content):

        conversation = Conversation.objects.get(
            id=self.conversation_id
        )

        user = self.scope["user"]

        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            content=content
        )

        conversation.save()

        return {
            "id": message.id,
            "content": message.content,
            "sender": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "position": user.position,
                "last_seen": user.last_seen.isoformat()
                if user.last_seen else None,
            },
            "created_at": message.created_at.isoformat(),
        }