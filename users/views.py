from django.db.models import Count

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
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

    serializer = EmployeeSerializer(employees, many=True)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def conversations(request):

    conversations = request.user.conversations.all().order_by("-updated_at")

    serializer = ConversationSerializer(conversations, many=True)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def messages(request, conversation_id):

    conversation = Conversation.objects.filter(
        id=conversation_id, participants=request.user
    ).first()

    if not conversation:
        return Response({"detail": "Söhbət tapılmadı."}, status=404)

    messages_queryset = Message.objects.filter(conversation=conversation)

    before = request.GET.get("before")

    if before:

        messages_queryset = messages_queryset.filter(id__lt=before)

    messages = list(messages_queryset.order_by("-id")[:20])

    messages.reverse()

    serializer = MessageSerializer(messages, many=True)

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_conversation(request):

    participant_ids = request.data.get("participants", [])

    if not participant_ids:
        return Response({"detail": "İştirakçı seçilməyib."}, status=400)

    participant_ids = [
        int(user_id) for user_id in participant_ids if str(user_id).isdigit()
    ]

    if len(participant_ids) != 1:
        return Response({"detail": "Yalnız bir əməkdaş seçilə bilər."}, status=400)

    other_user = User.objects.filter(id=participant_ids[0]).first()

    if not other_user:
        return Response({"detail": "Əməkdaş tapılmadı."}, status=404)

    # =========================
    # ÖZÜNLƏ SÖHBƏT
    # =========================

    if other_user.id == request.user.id:

        conversation = (
            Conversation.objects.annotate(
                participant_count=Count("participants", distinct=True)
            )
            .filter(participants=request.user, participant_count=1)
            .first()
        )

        if conversation:
            serializer = ConversationSerializer(conversation)
            return Response(serializer.data, status=200)

        conversation = Conversation.objects.create()
        conversation.participants.add(request.user)

        serializer = ConversationSerializer(conversation)

        return Response(serializer.data, status=201)

    # =========================
    # MÖVCUD SÖHBƏTİ TAP
    # =========================

    conversation = None

    for item in Conversation.objects.filter(participants=request.user):
        participant_ids = set(item.participants.values_list("id", flat=True))

        if participant_ids == {request.user.id, other_user.id}:
            conversation = item
            break

    if conversation:

        serializer = ConversationSerializer(conversation)

        return Response(serializer.data, status=200)

    # =========================
    # YENİ SÖHBƏT YARAT
    # =========================

    conversation = Conversation.objects.create()

    conversation.participants.set([request.user, other_user])

    serializer = ConversationSerializer(conversation)

    return Response(serializer.data, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_call(request, conversation_id):

    call_duration = request.data.get("call_duration")

    if call_duration is None:
        return Response({"detail": "Zəng müddəti göndərilməyib."}, status=400)

    try:
        call_duration = int(call_duration)

        if call_duration <= 0:
            raise ValueError

    except (ValueError, TypeError):
        return Response({"detail": "Zəng müddəti düzgün deyil."}, status=400)

    conversation = Conversation.objects.filter(
        id=conversation_id, participants=request.user
    ).first()

    if not conversation:
        return Response({"detail": "Söhbət tapılmadı."}, status=404)

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content="Səsli zəng",
        message_type="call",
        call_duration=call_duration,
        is_read=False,
    )

    conversation.save(update_fields=["updated_at"])

    serializer = MessageSerializer(message)

    # REAL-TIME WEBSOCKET GÖNDƏRİŞİ

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"chat_{conversation_id}",
        {
            "type": "chat_message",
            "message": dict(serializer.data),
        },
    )

    return Response(serializer.data, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_message(request, conversation_id):

    content = request.data.get("content", "").strip()

    if not content:
        return Response({"detail": "Mesaj boş ola bilməz."}, status=400)

    conversation = Conversation.objects.filter(
        id=conversation_id, participants=request.user
    ).first()

    if not conversation:
        return Response({"detail": "Söhbət tapılmadı."}, status=404)

    client_id = request.data.get("client_id")

    if client_id:
        client_id = str(client_id).strip()

    # =========================
    # IDEMPOTENCY
    # =========================

    if client_id:

        existing_message = Message.objects.filter(client_id=client_id).first()

        if existing_message:

            serializer = MessageSerializer(existing_message)

            return Response(serializer.data, status=200)

    # =========================
    # CREATE MESSAGE
    # =========================

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content,
        client_id=client_id,
    )

    serializer = MessageSerializer(message)

    return Response(serializer.data, status=201)
