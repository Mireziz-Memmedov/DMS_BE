import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Conversation


class CallConsumer(AsyncWebsocketConsumer):

    # =========================================================
    # CONNECT
    # =========================================================

    async def connect(self):

        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_group_name = f"user_{self.user.id}"

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name,
        )

        await self.accept()

    # =========================================================
    # DISCONNECT
    # =========================================================

    async def disconnect(self, close_code):

        if hasattr(self, "user_group_name"):

            await self.channel_layer.group_discard(
                self.user_group_name,
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

        call_types = {
            "call_offer",
            "call_answer",
            "ice_candidate",
            "call_reject",
            "call_end",
            "call_busy",
        }

        if message_type not in call_types:
            return

        await self.handle_call_signal(
            message_type,
            data,
        )

    # =========================================================
    # HANDLE CALL SIGNAL
    # =========================================================

    async def handle_call_signal(self, message_type, data):

        target_user_id = data.get("to_user_id")
        conversation_id = data.get("conversation_id")

        if target_user_id is None or conversation_id is None:
            return

        try:
            target_user_id = int(target_user_id)
            conversation_id = int(conversation_id)

        except (TypeError, ValueError):
            return

        if target_user_id == self.user.id:
            return

        # Hər iki istifadəçinin söhbət iştirakçısı olduğunu yoxla.
        if not await self.can_call_user(
            conversation_id,
            target_user_id,
        ):
            return

        signal = {
            "type": message_type,
            "from_user_id": self.user.id,
            "to_user_id": target_user_id,
            "conversation_id": conversation_id,
        }

        # =====================================================
        # OFFER / ANSWER
        # =====================================================

        if message_type in ("call_offer", "call_answer"):

            description = data.get("description")

            if not isinstance(description, dict):
                return

            expected_type = "offer" if message_type == "call_offer" else "answer"

            if description.get("type") != expected_type:
                return

            sdp = description.get("sdp")

            if not isinstance(sdp, str) or not sdp.strip():
                return

            signal["description"] = {
                "type": expected_type,
                "sdp": sdp,
            }

        # =====================================================
        # ICE CANDIDATE
        # =====================================================

        elif message_type == "ice_candidate":

            candidate = data.get("candidate")

            if not isinstance(candidate, dict):
                return

            if not isinstance(candidate.get("candidate"), str):
                return

            signal["candidate"] = candidate

        # =====================================================
        # REJECT / END / BUSY
        # =====================================================

        elif message_type in (
            "call_reject",
            "call_end",
            "call_busy",
        ):
            pass

        # =====================================================
        # SEND TO TARGET USER
        # =====================================================

        await self.channel_layer.group_send(
            f"user_{target_user_id}",
            {
                "type": "call_signal",
                "signal": signal,
            },
        )

    # =========================================================
    # CALL SIGNAL EVENT
    # =========================================================

    async def call_signal(self, event):

        signal = event["signal"]

        if signal["to_user_id"] != self.user.id:
            return

        await self.send(text_data=json.dumps(signal))

    # =========================================================
    # CHECK CONVERSATION PERMISSION
    # =========================================================

    @database_sync_to_async
    def can_call_user(self, conversation_id, target_user_id):

        return (
            Conversation.objects.filter(
                id=conversation_id,
                participants=self.user,
            )
            .filter(
                participants__id=target_user_id,
            )
            .exists()
        )
