# import json

# from django.utils import timezone
# from channels.db import database_sync_to_async
# from channels.generic.websocket import AsyncWebsocketConsumer

# from .models import Conversation, Message


# class ChatConsumer(AsyncWebsocketConsumer):

#     # =========================================================
#     # CONNECT
#     # =========================================================

#     async def connect(self):

#         self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]

#         self.room_group_name = f"chat_{self.conversation_id}"

#         self.user = self.scope["user"]

#         if not self.user.is_authenticated:
#             await self.close()
#             return

#         if not await self.is_conversation_participant():
#             await self.close()
#             return

#         await self.channel_layer.group_add(self.room_group_name, self.channel_name)

#         await self.accept()

#         await self.update_last_seen()

#     # =========================================================
#     # DISCONNECT
#     # =========================================================

#     async def disconnect(self, close_code):

#         if hasattr(self, "room_group_name"):

#             await self.channel_layer.group_discard(
#                 self.room_group_name, self.channel_name
#             )

#     # =========================================================
#     # RECEIVE
#     # =========================================================

#     async def receive(self, text_data):

#         try:
#             data = json.loads(text_data)
#         except (json.JSONDecodeError, TypeError):
#             return

#         if not isinstance(data, dict):
#             return

#         message_type = data.get("type")

#         # =====================================================
#         # PRESENCE
#         # =====================================================

#         if message_type == "presence":

#             await self.update_last_seen()

#             return

#         # =====================================================
#         # AUDIO CALL SIGNALING
#         # =====================================================

#         call_types = {
#             "call_offer",
#             "call_answer",
#             "ice_candidate",
#             "call_reject",
#             "call_end",
#             "call_busy",
#         }

#         if message_type in call_types:

#             await self.handle_call_signal(message_type, data)

#             return

#         # =====================================================
#         # MESSAGE
#         # =====================================================

#         if message_type not in (None, "message"):
#             return

#         message_text = data.get("message", "")

#         if not isinstance(message_text, str):
#             return

#         message_text = message_text.strip()

#         if not message_text:
#             return

#         client_id = data.get("client_id")

#         if client_id:

#             client_id = str(client_id).strip()

#             if not client_id:
#                 client_id = None

#         message = await self.create_message(message_text, client_id)

#         if message is None:
#             return

#         await self.update_last_seen()

#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 "type": "chat_message",
#                 "message": message,
#             },
#         )

#     # =========================================================
#     # CHAT MESSAGE EVENT
#     # =========================================================

#     async def chat_message(self, event):

#         await self.send(text_data=json.dumps({"message": event["message"]}))

#     # =========================================================
#     # CALL SIGNAL HANDLER
#     # =========================================================

#     async def handle_call_signal(self, message_type, data):

#         target_user_id = data.get("to_user_id")

#         if target_user_id is None:
#             return

#         try:
#             target_user_id = int(target_user_id)
#         except (TypeError, ValueError):
#             return

#         if target_user_id == self.user.id:
#             return

#         # Hədəf istifadəçi eyni söhbətin iştirakçısı olmalıdır.
#         if not await self.is_user_conversation_participant(target_user_id):
#             return

#         signal = {
#             "type": message_type,
#             "from_user_id": self.user.id,
#             "to_user_id": target_user_id,
#         }

#         # =====================================================
#         # OFFER / ANSWER
#         # =====================================================

#         if message_type in ("call_offer", "call_answer"):

#             description = data.get("description")

#             if not isinstance(description, dict):
#                 return

#             expected_type = "offer" if message_type == "call_offer" else "answer"

#             if description.get("type") != expected_type:
#                 return

#             sdp = description.get("sdp")

#             if not isinstance(sdp, str) or not sdp.strip():
#                 return

#             signal["description"] = {
#                 "type": expected_type,
#                 "sdp": sdp,
#             }

#         # =====================================================
#         # ICE CANDIDATE
#         # =====================================================

#         elif message_type == "ice_candidate":

#             candidate = data.get("candidate")

#             if not isinstance(candidate, dict):
#                 return

#             if not isinstance(candidate.get("candidate"), str):
#                 return

#             signal["candidate"] = candidate

#         # =====================================================
#         # REJECT / END / BUSY
#         # =====================================================

#         elif message_type in ("call_reject", "call_end", "call_busy"):

#             # Bu siqnallar üçün əlavə SDP tələb olunmur.
#             pass

#         # =====================================================
#         # FORWARD SIGNAL
#         # =====================================================

#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 "type": "call_signal",
#                 "signal": signal,
#             },
#         )

#     # =========================================================
#     # CALL SIGNAL EVENT
#     # =========================================================

#     async def call_signal(self, event):

#         signal = event["signal"]

#         # Siqnal yalnız hədəf istifadəçiyə göndərilir.
#         if signal["to_user_id"] != self.user.id:
#             return

#         await self.send(text_data=json.dumps(signal))

#     # =========================================================
#     # UPDATE LAST SEEN
#     # =========================================================

#     @database_sync_to_async
#     def update_last_seen(self):

#         user = self.scope["user"]

#         if user.is_authenticated:

#             user.last_seen = timezone.now()

#             user.save(update_fields=["last_seen"])

#     # =========================================================
#     # CONVERSATION PERMISSION
#     # =========================================================

#     @database_sync_to_async
#     def is_conversation_participant(self):

#         return Conversation.objects.filter(
#             id=self.conversation_id, participants=self.user
#         ).exists()

#     # =========================================================
#     # CHECK CALL TARGET
#     # =========================================================

#     @database_sync_to_async
#     def is_user_conversation_participant(self, user_id):

#         return (
#             Conversation.objects.filter(id=self.conversation_id, participants=self.user)
#             .filter(participants__id=user_id)
#             .exists()
#         )

#     # =========================================================
#     # CREATE MESSAGE
#     # =========================================================

#     @database_sync_to_async
#     def create_message(self, content, client_id=None):

#         conversation = Conversation.objects.get(id=self.conversation_id)

#         user = self.scope["user"]

#         # =====================================================
#         # IDEMPOTENCY
#         # =====================================================

#         if client_id:

#             existing_message = (
#                 Message.objects.select_related("sender")
#                 .filter(client_id=client_id)
#                 .first()
#             )

#             if existing_message:

#                 return {
#                     "id": existing_message.id,
#                     "client_id": existing_message.client_id,
#                     "content": existing_message.content,
#                     "sender": {
#                         "id": existing_message.sender.id,
#                         "username": existing_message.sender.username,
#                         "first_name": existing_message.sender.first_name,
#                         "last_name": existing_message.sender.last_name,
#                         "position": existing_message.sender.position,
#                         "last_seen": (
#                             existing_message.sender.last_seen.isoformat()
#                             if existing_message.sender.last_seen
#                             else None
#                         ),
#                     },
#                     "created_at": (existing_message.created_at.isoformat()),
#                 }

#         # =====================================================
#         # CREATE MESSAGE
#         # =====================================================

#         message = Message.objects.create(
#             conversation=conversation, sender=user, content=content, client_id=client_id
#         )

#         conversation.save()

#         return {
#             "id": message.id,
#             "client_id": message.client_id,
#             "content": message.content,
#             "sender": {
#                 "id": user.id,
#                 "username": user.username,
#                 "first_name": user.first_name,
#                 "last_name": user.last_name,
#                 "position": user.position,
#                 "last_seen": (user.last_seen.isoformat() if user.last_seen else None),
#             },
#             "created_at": message.created_at.isoformat(),
#         }


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
