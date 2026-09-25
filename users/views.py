from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, Conversation, Message

from .serializers import (
    LoginSerializer,
    EmployeeSerializer,
    ConversationSerializer,
    MessageSerializer,
)


class LoginView(TokenObtainPairView):

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employees(request):

    employees = User.objects.all()

    serializer = EmployeeSerializer(
        employees,
        many=True
    )

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def conversations(request):

    conversations = request.user.conversations.all()

    serializer = ConversationSerializer(
        conversations,
        many=True
    )

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def messages(request, conversation_id):

    messages = Message.objects.filter(
        conversation_id=conversation_id
    ).order_by("created_at")

    serializer = MessageSerializer(
        messages,
        many=True
    )

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_conversation(request):

    participant_ids = request.data.get("participants", [])

    if not participant_ids:
        return Response(
            {"detail": "İştirakçı seçilməyib."},
            status=400
        )

    participants = User.objects.filter(
        id__in=participant_ids
    )

    if not participants.exists():
        return Response(
            {"detail": "İştirakçılar tapılmadı."},
            status=400
        )

    conversation = Conversation.objects.create()

    conversation.participants.set(participants)

    conversation.participants.add(request.user)

    serializer = ConversationSerializer(conversation)

    return Response(
        serializer.data,
        status=201
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_message(request, conversation_id):

    content = request.data.get("content", "").strip()

    if not content:
        return Response(
            {"detail": "Mesaj boş ola bilməz."},
            status=400
        )

    conversation = Conversation.objects.filter(
        id=conversation_id,
        participants=request.user
    ).first()

    if not conversation:
        return Response(
            {"detail": "Söhbət tapılmadı."},
            status=404
        )

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content
    )

    serializer = MessageSerializer(message)

    return Response(
        serializer.data,
        status=201
    )