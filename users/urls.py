from django.urls import path

from . import views
from .views import LoginView

from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [

    path("login/", LoginView.as_view(), name="login"),

    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("employees/", views.employees, name="employees"),

]