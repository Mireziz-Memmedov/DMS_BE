from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import LoginSerializer
from .serializers import EmployeeSerializer


class LoginView(TokenObtainPairView):

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employees(request):

    employees = User.objects.all()
    
    serializer = EmployeeSerializer(employees, many=True)

    return Response(serializer.data)