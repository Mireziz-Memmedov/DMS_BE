import json

from django.utils import timezone
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Conversation, Message


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        self.conversation_id = (
            self.scope["url_route"]["kwargs"]["conversation_id"]
        )

        self.room_group_name = (
            f"chat_{self.conversation_id}"
        )

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        await self.update_last_seen()


    async def disconnect(self, close_code):

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )


    async def receive(self, text_data):

        data = json.loads(text_data)

        message_type = data.get("type")


        # =========================
        # PRESENCE / HEARTBEAT
        # =========================

        if message_type == "presence":

            await self.update_last_seen()

            return


        # =========================
        # MESSAGE
        # =========================

        message_text = data.get(
            "message",
            ""
        ).strip()

        if not message_text:
            return


        client_id = data.get("client_id")

        if client_id:
            client_id = str(client_id).strip()


        message = await self.create_message(
            message_text,
            client_id
        )


        await self.update_last_seen()


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
    def update_last_seen(self):

        user = self.scope["user"]

        if user.is_authenticated:

            user.last_seen = timezone.now()

            user.save(
                update_fields=["last_seen"]
            )


    @database_sync_to_async
    def create_message(
        self,
        content,
        client_id=None
    ):

        conversation = Conversation.objects.get(
            id=self.conversation_id
        )

        user = self.scope["user"]


        # =========================
        # IDEMPOTENCY
        # =========================
        #
        # Eyni client_id ilə mesaj artıq
        # yaradılıbsa, ikinci dəfə yaratma.
        #

        if client_id:

            existing_message = (
                Message.objects
                .select_related(
                    "sender"
                )
                .filter(
                    client_id=client_id
                )
                .first()
            )

            if existing_message:

                return {
                    "id": existing_message.id,

                    "client_id": existing_message.client_id,

                    "content": existing_message.content,

                    "sender": {
                        "id": existing_message.sender.id,
                        "username": existing_message.sender.username,
                        "first_name": existing_message.sender.first_name,
                        "last_name": existing_message.sender.last_name,
                        "position": existing_message.sender.position,
                        "last_seen": (
                            existing_message.sender.last_seen.isoformat()
                            if existing_message.sender.last_seen
                            else None
                        ),
                    },

                    "created_at": (
                        existing_message.created_at.isoformat()
                    ),
                }


        # =========================
        # CREATE MESSAGE
        # =========================

        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            content=content,
            client_id=client_id
        )


        conversation.save()


        return {
            "id": message.id,

            "client_id": message.client_id,

            "content": message.content,

            "sender": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "position": user.position,
                "last_seen": (
                    user.last_seen.isoformat()
                    if user.last_seen
                    else None
                ),
            },

            "created_at": message.created_at.isoformat(),
        }
