from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from apps.orders.models import Order


@dataclass
class OrderValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_order_for_export(order: Order) -> OrderValidationResult:
    errors: list[str] = []
    if not order.company_id:
        errors.append('У заказа не указана компания.')
    if not order.user_id:
        errors.append('У заказа не указан пользователь.')
    if order.total <= Decimal('0'):
        errors.append('Сумма заказа должна быть больше нуля.')
    items = list(order.items.select_related('product').all())
    if not items:
        errors.append('У заказа нет строк.')
    for item in items:
        if item.qty <= 0:
            errors.append(f'Строка {item.pk}: количество должно быть больше нуля.')
        if item.price < 0:
            errors.append(f'Строка {item.pk}: цена не может быть отрицательной.')
        product_code = item.product_code_snapshot or getattr(item.product, 'code', '') or getattr(item.product, 'external_id', '')
        if not product_code:
            errors.append(f'Строка {item.pk}: отсутствует код товара для экспорта.')
    return OrderValidationResult(ok=not errors, errors=errors)
