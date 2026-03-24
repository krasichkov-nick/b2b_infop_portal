from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import CompanyMeSerializer


class CompanyMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, 'company_profile', None)
        if not profile:
            return Response({'detail': 'Профиль компании не найден.'}, status=404)
        return Response(CompanyMeSerializer(profile).data)
