from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Conversation, Message

class LoginSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):

        data = super().validate(attrs)

        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "email": self.user.email,
            "position": self.user.position,
            "last_seen": self.user.last_seen,
        }

        return data


class EmployeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "position",
            "email",
        ]

class UserSerializer(serializers.ModelSerializer):

    is_online = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "position",
            "last_seen",
            "is_online",
        ]
    
    def get_is_online(self, obj):

        if not obj.last_seen:
            return False

        seconds = (
            timezone.now() - obj.last_seen
        ).total_seconds()

        return seconds < 60


class ConversationSerializer(serializers.ModelSerializer):

    participants = UserSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Conversation
        fields = [
            "id",
            "participants",
            "created_at",
            "updated_at",
        ]


class MessageSerializer(serializers.ModelSerializer):

    sender = UserSerializer(
        read_only=True
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender",
            "content",
            "is_read",
            "created_at",
        ]