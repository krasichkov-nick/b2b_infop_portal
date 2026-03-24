from django.contrib import admin
from .models import Company, CompanyUser


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'external_id', 'tax_id', 'price_type', 'min_order_amount', 'is_active')
    list_filter = ('is_active', 'price_type')
    search_fields = ('name', 'external_id', 'tax_id', 'email', 'phone')


@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'company__name')
