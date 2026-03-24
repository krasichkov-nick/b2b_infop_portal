from rest_framework import serializers
from .models import CompanyUser


class CompanyMeSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    price_type = serializers.CharField(source='company.price_type.code', read_only=True)

    class Meta:
        model = CompanyUser
        fields = ['role', 'company_name', 'price_type']
