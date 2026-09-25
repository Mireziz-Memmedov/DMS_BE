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

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "position",
            "last_seen",
        ]


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