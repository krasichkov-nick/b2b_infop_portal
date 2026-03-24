from __future__ import annotations

from django.conf import settings
from django.db import models
from apps.catalog.models import PriceType


class Company(models.Model):
    name = models.CharField('Компания', max_length=255)
    external_id = models.CharField('Внешний ID', max_length=128, blank=True, unique=True, db_index=True)
    tax_id = models.CharField('ИНН/налоговый номер', max_length=32, blank=True)
    email = models.EmailField('Email', blank=True)
    phone = models.CharField('Телефон', max_length=64, blank=True)
    address = models.CharField('Адрес', max_length=500, blank=True)
    legal_address = models.CharField('Юридический адрес', max_length=500, blank=True)
    shipping_address = models.CharField('Адрес доставки', max_length=500, blank=True)
    manager_name = models.CharField('Ответственный менеджер', max_length=255, blank=True)
    manager_email = models.EmailField('Email менеджера', blank=True)
    credit_limit = models.DecimalField('Кредитный лимит', max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField('Активна', default=True)
    price_type = models.ForeignKey(PriceType, verbose_name='Тип цены', on_delete=models.SET_NULL, blank=True, null=True)
    min_order_amount = models.DecimalField('Минимальная сумма заказа', max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.external_id:
            self.external_id = f'company-{self.pk}'
            super().save(update_fields=['external_id'])


class CompanyUser(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Владелец'),
        ('manager', 'Менеджер'),
        ('buyer', 'Закупщик'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_profile')
    company = models.ForeignKey(Company, verbose_name='Компания', on_delete=models.CASCADE, related_name='users')
    role = models.CharField('Роль', max_length=16, choices=ROLE_CHOICES, default='buyer')

    class Meta:
        verbose_name = 'Пользователь компании'
        verbose_name_plural = 'Пользователи компаний'

    def __str__(self):
        return f'{self.user} -> {self.company}'
