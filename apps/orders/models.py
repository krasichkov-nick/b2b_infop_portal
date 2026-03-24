from __future__ import annotations

import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.customers.models import Company
from apps.catalog.models import Product


class Order(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('approved', 'Подтвержден'),
        ('exported', 'Выгружен в ERP'),
        ('invoiced', 'Выставлен счет'),
        ('paid', 'Оплачен'),
        ('overdue', 'Просрочен'),
        ('shipped', 'Отгружен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    ERP_EXPORT_STATES = [
        ('new', 'Новый'),
        ('validated', 'Проверен'),
        ('exported', 'Выгружен'),
        ('imported', 'Импортирован в ERP'),
        ('error', 'Ошибка'),
    ]

    company = models.ForeignKey(Company, verbose_name='Компания', on_delete=models.PROTECT, related_name='orders')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Пользователь', on_delete=models.PROTECT, related_name='orders')
    site_number = models.CharField('Номер на сайте', max_length=64, unique=True)
    external_uid = models.CharField('Внешний UID', max_length=128, unique=True, blank=True, db_index=True)
    external_number = models.CharField('Номер в ERP', max_length=64, blank=True)
    erp_document_number = models.CharField('Номер документа ERP', max_length=64, blank=True)
    status = models.CharField('Статус', max_length=16, choices=STATUS_CHOICES, default='new')
    erp_export_state = models.CharField('Состояние выгрузки ERP', max_length=16, choices=ERP_EXPORT_STATES, default='new', db_index=True)
    erp_status_code = models.CharField('Код статуса ERP', max_length=64, blank=True)
    erp_status_label = models.CharField('Статус ERP', max_length=255, blank=True)
    erp_updated_at = models.DateTimeField('Обновлено из ERP', blank=True, null=True)
    exported_at = models.DateTimeField('Выгружен в ERP', blank=True, null=True)
    locked_after_export = models.BooleanField('Заблокирован после выгрузки', default=False)
    imported_to_erp = models.BooleanField('Импортирован в ERP', default=False)
    currency = models.CharField('Валюта', max_length=8, default='RUB')
    subtotal = models.DecimalField('Сумма', max_digits=14, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField('Итого', max_digits=14, decimal_places=2, default=Decimal('0'))
    comment = models.TextField('Комментарий', blank=True)
    customer_comment = models.TextField('Комментарий клиента', blank=True)
    manager_comment = models.TextField('Комментарий менеджера', blank=True)
    erp_sync_error = models.TextField('Ошибка ERP', blank=True)
    last_export_hash = models.CharField('Хеш последней выгрузки', max_length=64, blank=True)
    last_export_batch = models.ForeignKey(
        'integrations.ExchangeBatch', verbose_name='Последний пакет выгрузки',
        on_delete=models.SET_NULL, blank=True, null=True, related_name='orders'
    )
    erp_last_payload_ref = models.ForeignKey(
        'integrations.ExchangeArtifact', verbose_name='Последний входящий файл ERP',
        on_delete=models.SET_NULL, blank=True, null=True, related_name='orders_last_seen'
    )
    can_repeat = models.BooleanField('Можно повторить', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return self.site_number

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.external_uid:
            self.external_uid = f'order-{self.pk}-{uuid.uuid4().hex[:8]}'
            super().save(update_fields=['external_uid'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name='Заказ', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, verbose_name='Товар', on_delete=models.PROTECT, related_name='order_items')
    product_code_snapshot = models.CharField('Код товара', max_length=128)
    product_name_snapshot = models.CharField('Название товара', max_length=500)
    qty = models.DecimalField('Количество', max_digits=14, decimal_places=3)
    price = models.DecimalField('Цена', max_digits=14, decimal_places=2)
    line_total = models.DecimalField('Сумма строки', max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = 'Строка заказа'
        verbose_name_plural = 'Строки заказа'

    def __str__(self):
        return f'{self.order.site_number} / {self.product_code_snapshot}'


class OrderStatusEvent(models.Model):
    SOURCE_CHOICES = [('site', 'Сайт'), ('erp', 'ERP'), ('system', 'Система')]

    order = models.ForeignKey(Order, verbose_name='Заказ', on_delete=models.CASCADE, related_name='status_events')
    previous_status = models.CharField('Предыдущий статус', max_length=32, blank=True)
    new_status = models.CharField('Новый статус', max_length=32)
    source = models.CharField('Источник', max_length=16, choices=SOURCE_CHOICES, default='system')
    comment = models.TextField('Комментарий', blank=True)
    external_number = models.CharField('Номер ERP', max_length=64, blank=True)
    raw_status_code = models.CharField('Сырой код статуса', max_length=128, blank=True)
    raw_status_label = models.CharField('Сырое название статуса', max_length=255, blank=True)
    source_file = models.CharField('Файл-источник', max_length=500, blank=True)
    payload_excerpt = models.TextField('Фрагмент исходных данных', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    applied_at = models.DateTimeField('Применено', default=timezone.now)

    class Meta:
        verbose_name = 'История статуса заказа'
        verbose_name_plural = 'История статусов заказов'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.site_number}: {self.new_status}'
