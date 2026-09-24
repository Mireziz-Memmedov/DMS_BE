from django.urls import path
from . import views
from .views import LoginView


urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("employees/", views.employees, name="employees"),
]