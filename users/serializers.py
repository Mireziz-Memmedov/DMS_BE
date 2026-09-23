from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User

class LoginSerializer(TokenObtainPairSerializer):
    pass


# class UserSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = User
#         fields = "__all__"