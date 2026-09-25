from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):

    position = models.CharField(
        max_length=150,
        blank=True
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.username


class Conversation(models.Model):

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="conversations"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

class Message(models.Model):

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )

    content = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
