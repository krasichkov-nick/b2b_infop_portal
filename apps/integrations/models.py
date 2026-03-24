from __future__ import annotations

from django.db import models


class IntegrationProfile(models.Model):
    code = models.SlugField('Код профиля', max_length=64, unique=True)
    name = models.CharField('Название', max_length=255)
    is_active = models.BooleanField('Активен', default=True)

    import_xml_path = models.CharField('Путь к import.xml', max_length=1024, blank=True)
    offers_xml_path = models.CharField('Путь к offers.xml', max_length=1024, blank=True)
    images_dir_path = models.CharField('Путь к import_files', max_length=1024, blank=True)
    export_orders_path = models.CharField('Путь к выгрузке orders.xml', max_length=1024, blank=True)
    status_feed_path = models.CharField('Путь к файлу статусов заказов', max_length=1024, blank=True)
    archive_path = models.CharField('Каталог архива обмена', max_length=1024, blank=True)

    run_every_minutes = models.PositiveIntegerField('Интервал запуска, минут', default=15)
    export_only_new = models.BooleanField('Экспортировать только новые заказы', default=True)
    auto_export_enabled = models.BooleanField('Автоэкспорт заказов', default=True)
    auto_status_import_enabled = models.BooleanField('Автоимпорт статусов', default=True)
    notify_emails = models.CharField('Email для уведомлений', max_length=1024, blank=True)

    last_run_at = models.DateTimeField('Последний запуск', blank=True, null=True)
    last_success_at = models.DateTimeField('Последний успешный запуск', blank=True, null=True)
    last_error = models.TextField('Последняя ошибка', blank=True)

    class Meta:
        verbose_name = 'Профиль интеграции'
        verbose_name_plural = 'Профили интеграции'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def notify_email_list(self):
        return [item.strip() for item in (self.notify_emails or '').split(',') if item.strip()]


class ExchangeBatch(models.Model):
    DIRECTION_CHOICES = [('export_orders', 'Экспорт заказов'), ('import_statuses', 'Импорт статусов'), ('system', 'Система')]
    STATUS_CHOICES = [('created', 'Создан'), ('ok', 'Успешно'), ('warning', 'Предупреждение'), ('error', 'Ошибка')]

    code = models.CharField('Код пакета', max_length=64, unique=True, db_index=True)
    direction = models.CharField('Направление', max_length=32, choices=DIRECTION_CHOICES)
    profile = models.ForeignKey(IntegrationProfile, verbose_name='Профиль', on_delete=models.SET_NULL, blank=True, null=True, related_name='batches')
    status = models.CharField('Статус', max_length=16, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    started_at = models.DateTimeField('Начат', blank=True, null=True)
    finished_at = models.DateTimeField('Завершен', blank=True, null=True)
    orders_count = models.PositiveIntegerField('Заказов', default=0)
    success_count = models.PositiveIntegerField('Успешно', default=0)
    error_count = models.PositiveIntegerField('Ошибок', default=0)
    file_path = models.CharField('Путь к основному файлу', max_length=1024, blank=True)
    checksum = models.CharField('Checksum', max_length=64, blank=True)
    comment = models.TextField('Комментарий', blank=True)

    class Meta:
        verbose_name = 'Пакет обмена'
        verbose_name_plural = 'Пакеты обмена'
        ordering = ['-created_at']

    def __str__(self):
        return self.code


class ExchangeArtifact(models.Model):
    KIND_CHOICES = [('orders_xml', 'orders.xml'), ('status_xml', 'status xml'), ('status_csv', 'status csv'), ('log', 'log')]

    batch = models.ForeignKey(ExchangeBatch, verbose_name='Пакет', on_delete=models.CASCADE, related_name='artifacts')
    kind = models.CharField('Тип файла', max_length=32, choices=KIND_CHOICES)
    file_path = models.CharField('Путь к файлу', max_length=1024)
    checksum = models.CharField('Checksum', max_length=64, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Артефакт обмена'
        verbose_name_plural = 'Артефакты обмена'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.batch.code}:{self.kind}'


class ERPStatusMapping(models.Model):
    source_code = models.CharField('Код ERP', max_length=128, blank=True)
    source_label = models.CharField('Статус ERP', max_length=255, blank=True)
    internal_status = models.CharField('Внутренний статус', max_length=32)
    is_terminal = models.BooleanField('Терминальный', default=False)
    notify_customer = models.BooleanField('Уведомлять клиента', default=True)

    class Meta:
        verbose_name = 'Карта статуса ERP'
        verbose_name_plural = 'Карты статусов ERP'
        ordering = ['source_code', 'source_label']
        constraints = [
            models.UniqueConstraint(fields=['source_code', 'source_label'], name='uniq_erp_status_mapping_pair')
        ]

    def __str__(self):
        return self.source_code or self.source_label or self.internal_status


class ExchangeLog(models.Model):
    DIRECTION_CHOICES = [('import', 'Импорт'), ('export', 'Экспорт'), ('status', 'Статусы'), ('system', 'Система')]
    STATUS_CHOICES = [('ok', 'Успешно'), ('warning', 'Предупреждение'), ('error', 'Ошибка')]

    profile = models.ForeignKey(
        IntegrationProfile,
        verbose_name='Профиль',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='logs',
    )
    batch = models.ForeignKey(
        ExchangeBatch,
        verbose_name='Пакет',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='logs',
    )
    direction = models.CharField('Направление', max_length=16, choices=DIRECTION_CHOICES)
    source = models.CharField('Источник', max_length=255)
    file_name = models.CharField('Файл', max_length=500, blank=True)
    status = models.CharField('Статус', max_length=16, choices=STATUS_CHOICES)
    message = models.TextField('Сообщение')
    payload_excerpt = models.TextField('Фрагмент', blank=True)
    started_at = models.DateTimeField('Начало', blank=True, null=True)
    finished_at = models.DateTimeField('Окончание', blank=True, null=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Лог обмена'
        verbose_name_plural = 'Логи обмена'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.direction}:{self.status}:{self.file_name or self.source}'
