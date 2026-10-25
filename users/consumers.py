import json

from django.utils import timezone
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):

    # =========================================================
    # CONNECT
    # =========================================================

    async def connect(self):

        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]

        if not self.user.is_authenticated:
            await self.close()
            return

        if not await self.is_conversation_participant():
            await self.close()
            return

        self.room_group_name = f"chat_{self.conversation_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        await self.update_last_seen()

    # =========================================================
    # DISCONNECT
    # =========================================================

    async def disconnect(self, close_code):

        if hasattr(self, "room_group_name"):

            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    # =========================================================
    # RECEIVE
    # =========================================================

    async def receive(self, text_data):

        try:
            data = json.loads(text_data)

        except (json.JSONDecodeError, TypeError):
            return

        if not isinstance(data, dict):
            return

        message_type = data.get("type")

        # =====================================================
        # PRESENCE
        # =====================================================

        if message_type == "presence":

            await self.update_last_seen()

            return

        # =====================================================
        # CHAT MESSAGE
        # =====================================================

        if message_type not in (None, "message"):
            return

        message_text = data.get("message", "")

        if not isinstance(message_text, str):
            return

        message_text = message_text.strip()

        if not message_text:
            return

        client_id = data.get("client_id")

        if client_id is not None:

            client_id = str(client_id).strip()

            if not client_id:
                client_id = None

        message = await self.create_message(
            message_text,
            client_id,
        )

        if message is None:
            return

        await self.update_last_seen()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
            },
        )

    # =========================================================
    # CHAT MESSAGE EVENT
    # =========================================================

    async def chat_message(self, event):

        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                }
            )
        )

    # =========================================================
    # UPDATE LAST SEEN
    # =========================================================

    @database_sync_to_async
    def update_last_seen(self):

        user = self.scope["user"]

        if user.is_authenticated:

            user.last_seen = timezone.now()

            user.save(update_fields=["last_seen"])

    # =========================================================
    # CONVERSATION PERMISSION
    # =========================================================

    @database_sync_to_async
    def is_conversation_participant(self):

        return Conversation.objects.filter(
            id=self.conversation_id,
            participants=self.user,
        ).exists()

    # =========================================================
    # CREATE MESSAGE
    # =========================================================

    @database_sync_to_async
    def create_message(self, content, client_id=None):

        conversation = Conversation.objects.get(id=self.conversation_id)

        user = self.scope["user"]

        # =====================================================
        # IDEMPOTENCY
        # =====================================================

        if client_id:

            existing_message = (
                Message.objects.select_related("sender")
                .filter(
                    conversation=conversation,
                    sender=user,
                    client_id=client_id,
                )
                .first()
            )

            if existing_message:

                return self.serialize_message(existing_message)

        # =====================================================
        # CREATE MESSAGE
        # =====================================================

        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            content=content,
            client_id=client_id,
        )

        conversation.save()

        return self.serialize_message(message)

    # =========================================================
    # SERIALIZE MESSAGE
    # =========================================================

    def serialize_message(self, message):

        sender = message.sender

        return {
            "id": message.id,
            "client_id": message.client_id,
            "content": message.content,
            "sender": {
                "id": sender.id,
                "username": sender.username,
                "first_name": sender.first_name,
                "last_name": sender.last_name,
                "position": sender.position,
                "last_seen": (
                    sender.last_seen.isoformat() if sender.last_seen else None
                ),
            },
            "created_at": message.created_at.isoformat(),
        }
