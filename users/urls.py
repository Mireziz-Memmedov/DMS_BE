from django.urls import path

from . import views
from .views import LoginView

from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [

    path(
        "login/",
        LoginView.as_view(),
        name="login"
    ),

    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh"
    ),

    path(
        "employees/",
        views.employees,
        name="employees"
    ),

    path(
        "conversations/",
        views.conversations,
        name="conversations"
    ),

    path(
        "conversations/create/",
        views.create_conversation,
        name="create_conversation"
    ),

    path(
        "conversations/<int:conversation_id>/messages/",
        views.messages,
        name="messages"
    ),

    path(
        "conversations/<int:conversation_id>/messages/create/",
        views.create_message,
        name="create_message"
    ),

]