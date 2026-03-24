from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import PriceType, Product, ProductPrice
from apps.customers.models import Company
from apps.orders.models import Order, OrderItem, OrderStatusEvent
from apps.integrations.services.notifications import notify_new_order, notify_order_status_changed


class OrderValidationError(Exception):
    pass


@dataclass
class RequestedItem:
    product: Product
    qty: Decimal
    price: Decimal
    line_total: Decimal


def _normalize_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(',', '.').strip())
    except (InvalidOperation, AttributeError):
        raise OrderValidationError(f'Некорректное количество: {value!r}')


def get_company_price_type(company: Company | None) -> PriceType | None:
    return (company.price_type if company and company.price_type_id else None) or PriceType.objects.filter(is_default=True).first()


def get_product_price_for_company(product: Product, company: Company | None) -> ProductPrice | None:
    requested_price_type = get_company_price_type(company)
    price_obj = None
    if requested_price_type:
        price_obj = ProductPrice.objects.filter(product=product, price_type=requested_price_type).first()
    if not price_obj:
        price_obj = ProductPrice.objects.filter(product=product).order_by('-price_type__is_default', 'id').first()
    return price_obj


def validate_requested_items(company: Company, raw_items: Iterable[dict]) -> list[RequestedItem]:
    prepared: list[RequestedItem] = []
    seen_any = False
    for item in raw_items:
        code = (item.get('product_code') or item.get('code') or '').strip()
        qty = _normalize_decimal(item.get('qty', '0'))
        if not code:
            continue
        seen_any = True
        if qty <= 0:
            raise OrderValidationError(f'Количество для товара {code} должно быть больше нуля.')

        product = Product.objects.filter(code=code, is_published=True).first()
        if not product:
            raise OrderValidationError(f'Товар с кодом {code} не найден или не опубликован.')

        if qty < product.min_order_qty:
            raise OrderValidationError(
                f'Для товара {product.code} количество {qty} меньше минимального заказа {product.min_order_qty}.'
            )

        multiplicity = product.multiplicity or Decimal('1')
        if multiplicity > 0:
            units = qty / multiplicity
            if units != units.quantize(Decimal('1')):
                raise OrderValidationError(
                    f'Для товара {product.code} количество {qty} не кратно шагу {multiplicity}.'
                )

        price_obj = get_product_price_for_company(product, company)
        if not price_obj:
            raise OrderValidationError(f'Для товара {product.code} не найдена цена.')

        line_total = qty * price_obj.amount
        prepared.append(RequestedItem(product=product, qty=qty, price=price_obj.amount, line_total=line_total))

    if not seen_any or not prepared:
        raise OrderValidationError('Не добавлено ни одной валидной позиции.')

    subtotal = sum((row.line_total for row in prepared), Decimal('0'))
    if company.min_order_amount and subtotal < company.min_order_amount:
        raise OrderValidationError(
            f'Минимальная сумма заказа для компании {company.name}: {company.min_order_amount}. Текущая сумма: {subtotal}.'
        )
    return prepared


def register_order_status_event(
    *,
    order: Order,
    new_status: str,
    source: str = 'system',
    comment: str = '',
    external_number: str = '',
    raw_status_code: str = '',
    raw_status_label: str = '',
    source_file: str = '',
    payload_excerpt: str = '',
    notify: bool = True,
) -> OrderStatusEvent:
    previous_status = order.status or ''
    ext_changed = bool(external_number and external_number != order.external_number)
    status_changed = previous_status != new_status
    changed = status_changed or ext_changed or bool(comment) or bool(raw_status_code) or bool(raw_status_label)

    if external_number and ext_changed:
        order.external_number = external_number
        order.erp_document_number = external_number
    if status_changed:
        order.status = new_status

    if source == 'erp':
        order.erp_status_code = raw_status_code or new_status
        order.erp_status_label = raw_status_label or new_status
        order.erp_updated_at = timezone.now()
        if new_status in {'approved', 'processing', 'invoiced', 'paid', 'overdue', 'shipped', 'completed', 'cancelled'}:
            order.erp_export_state = 'imported'

    if changed:
        update_fields = []
        for name in ('status', 'external_number', 'erp_document_number', 'erp_status_code', 'erp_status_label', 'erp_updated_at', 'erp_export_state'):
            if getattr(order, name, None) is not None:
                update_fields.append(name)
        order.save(update_fields=sorted(set(update_fields)))
        event = OrderStatusEvent.objects.create(
            order=order,
            previous_status=previous_status,
            new_status=new_status,
            source=source,
            comment=comment or '',
            external_number=external_number or order.external_number or '',
            raw_status_code=raw_status_code or '',
            raw_status_label=raw_status_label or '',
            source_file=source_file or '',
            payload_excerpt=payload_excerpt or '',
        )
        if notify:
            notify_order_status_changed(order=order, previous_status=previous_status, comment=comment)
        return event
    return OrderStatusEvent.objects.filter(order=order).order_by('-created_at').first()


@transaction.atomic
def create_order_for_user(*, user, raw_items: Iterable[dict], comment: str = '', status: str = 'new') -> Order:
    profile = getattr(user, 'company_profile', None)
    if not profile or not profile.company_id:
        raise OrderValidationError('Пользователь не привязан к компании.')
    company = profile.company
    prepared = validate_requested_items(company, raw_items)

    site_number = timezone.now().strftime('WEB%Y%m%d%H%M%S%f')
    order = Order.objects.create(
        company=company,
        user=user,
        site_number=site_number,
        status=status,
        erp_export_state='new',
        comment=comment or '',
        customer_comment=comment or '',
    )
    subtotal = Decimal('0')
    for row in prepared:
        OrderItem.objects.create(
            order=order,
            product=row.product,
            product_code_snapshot=row.product.code,
            product_name_snapshot=row.product.name,
            qty=row.qty,
            price=row.price,
            line_total=row.line_total,
        )
        subtotal += row.line_total

    order.subtotal = subtotal
    order.total = subtotal
    order.erp_export_state = 'validated'
    order.save(update_fields=['subtotal', 'total', 'erp_export_state'])
    OrderStatusEvent.objects.create(
        order=order,
        previous_status='',
        new_status=order.status,
        source='site',
        comment='Заказ создан на сайте.',
    )
    notify_new_order(order)
    return order
