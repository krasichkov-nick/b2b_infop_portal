from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail


def _clean_recipients(*groups):
    recipients = []
    seen = set()
    for group in groups:
        for item in group or []:
            email = (item or '').strip()
            if not email or email in seen:
                continue
            seen.add(email)
            recipients.append(email)
    return recipients


def notify_new_order(order):
    recipients = _clean_recipients(
        [order.user.email, order.company.email],
        getattr(settings, 'MANAGER_NOTIFICATION_EMAILS', []),
    )
    if not recipients:
        return 0
    subject = f'Новый B2B-заказ {order.site_number}'
    body = (
        f'Создан новый заказ {order.site_number}.\n'
        f'Компания: {order.company.name}\n'
        f'Сумма: {order.total}\n'
        f'Статус: {order.get_status_display()}\n'
        f'Комментарий: {order.comment or "-"}\n'
    )
    return send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True)


def notify_order_status_changed(*, order, previous_status: str, comment: str = ''):
    recipients = _clean_recipients([order.user.email, order.company.email])
    if not recipients:
        return 0
    subject = f'Обновление заказа {order.site_number}'
    body = (
        f'Заказ {order.site_number} изменил статус.\n'
        f'Было: {previous_status or "—"}\n'
        f'Стало: {order.get_status_display()}\n'
        f'Номер ERP: {order.external_number or "-"}\n'
        f'Комментарий: {comment or "-"}\n'
    )
    return send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True)


def notify_sync_failure(*, recipients, profile_name: str, message: str):
    recipients = _clean_recipients(recipients, getattr(settings, 'MANAGER_NOTIFICATION_EMAILS', []))
    if not recipients:
        return 0
    subject = f'Ошибка интеграции B2B: {profile_name}'
    body = f'Профиль: {profile_name}\nОшибка: {message}\n'
    return send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True)
