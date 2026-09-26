from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken


User = get_user_model()


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):

        query_string = scope["query_string"].decode()

        query_params = parse_qs(query_string)

        token = query_params.get("token", [None])[0]

        scope["user"] = await self.get_user(token)

        return await super().__call__(
            scope,
            receive,
            send
        )


    @database_sync_to_async
    def get_user(self, token):

        if not token:
            return None

        try:

            access_token = AccessToken(token)

            user_id = access_token["user_id"]

            return User.objects.get(
                id=user_id
            )

        except Exception:

            return None