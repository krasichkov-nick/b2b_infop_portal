from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from django.utils import timezone

from apps.integrations.models import ExchangeArtifact, ExchangeBatch, ExchangeLog, IntegrationProfile
from apps.integrations.services.order_validation import validate_order_for_export
from apps.orders.models import Order
from apps.orders.services import register_order_status_event

COMMERCE_NS = 'urn:1C.ru:commerceml_2'
ET.register_namespace('', COMMERCE_NS)


def _cml(tag: str) -> str:
    return f'{{{COMMERCE_NS}}}{tag}'


@dataclass
class ExportResult:
    path: Path
    batch: ExchangeBatch
    exported_orders: list[Order]
    skipped: list[tuple[Order, list[str]]]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _archive_output_path(output_path: Path, profile: IntegrationProfile | None, batch_code: str) -> Path:
    if profile and profile.archive_path:
        base = Path(profile.archive_path)
    else:
        base = output_path.parent / 'archive'
    dated = base / 'orders' / timezone.now().strftime('%Y-%m-%d')
    dated.mkdir(parents=True, exist_ok=True)
    return dated / f'orders_{batch_code}.xml'


def _export_queryset(*, only_new: bool, force: bool, order_ids: list[int] | None = None):
    qs = Order.objects.select_related('company', 'user').prefetch_related('items__product')
    if order_ids:
        qs = qs.filter(pk__in=order_ids)
    elif only_new and not force:
        qs = qs.filter(erp_export_state__in=['new', 'validated'])
    if not force:
        qs = qs.exclude(locked_after_export=True, erp_export_state__in=['exported', 'imported'])
    return qs.order_by('pk')


def export_orders_xml(
    output_path: str | Path,
    only_new: bool = True,
    profile: IntegrationProfile | None = None,
    *,
    force: bool = False,
    order_ids: list[int] | None = None,
    batch_comment: str = '',
) -> ExportResult:
    output_path = Path(output_path)
    batch_code = timezone.now().strftime('EXP%Y%m%d%H%M%S%f')
    batch = ExchangeBatch.objects.create(
        code=batch_code,
        direction='export_orders',
        profile=profile,
        status='created',
        started_at=timezone.now(),
        comment=batch_comment or '',
    )
    root = ET.Element(
        _cml('КоммерческаяИнформация'),
        ВерсияСхемы='2.10',
        ДатаФормирования=timezone.now().strftime('%Y-%m-%dT%H:%M:%S'),
    )

    exported_orders: list[Order] = []
    skipped: list[tuple[Order, list[str]]] = []

    for order in _export_queryset(only_new=only_new, force=force, order_ids=order_ids):
        validation = validate_order_for_export(order)
        if not validation.ok:
            skipped.append((order, validation.errors))
            ExchangeLog.objects.create(
                profile=profile,
                batch=batch,
                direction='export',
                source='CommerceML',
                file_name=output_path.name,
                status='warning',
                message=f'Заказ {order.site_number} пропущен при экспорте.',
                payload_excerpt='; '.join(validation.errors),
            )
            order.erp_export_state = 'error'
            order.erp_sync_error = '; '.join(validation.errors)
            order.save(update_fields=['erp_export_state', 'erp_sync_error'])
            continue

        doc = ET.SubElement(root, _cml('Документ'))
        ET.SubElement(doc, _cml('Ид')).text = order.external_uid
        ET.SubElement(doc, _cml('Номер')).text = order.site_number
        ET.SubElement(doc, _cml('Дата')).text = order.created_at.strftime('%Y-%m-%d')
        ET.SubElement(doc, _cml('ХозОперация')).text = 'Заказ товара'
        ET.SubElement(doc, _cml('Роль')).text = 'Продавец'
        ET.SubElement(doc, _cml('Валюта')).text = 'руб' if str(order.currency).upper() in {'RUB', 'RUR'} else str(order.currency)
        ET.SubElement(doc, _cml('Курс')).text = '1'
        ET.SubElement(doc, _cml('Сумма')).text = f'{order.total:.2f}'
        ET.SubElement(doc, _cml('Время')).text = order.created_at.strftime('%H:%M:%S')
        ET.SubElement(doc, _cml('Комментарий')).text = order.comment or order.customer_comment or ''

        contractors = ET.SubElement(doc, _cml('Контрагенты'))
        contractor = ET.SubElement(contractors, _cml('Контрагент'))
        company = order.company
        company_id = company.external_id or f'company-{company.pk}'
        ET.SubElement(contractor, _cml('Ид')).text = company_id
        ET.SubElement(contractor, _cml('Наименование')).text = company.name
        ET.SubElement(contractor, _cml('Роль')).text = 'Покупатель'
        ET.SubElement(contractor, _cml('ПолноеНаименование')).text = company.name

        contact_name = (order.user.get_full_name() or '').strip() if hasattr(order.user, 'get_full_name') else ''
        if not contact_name:
            contact_name = getattr(order.user, 'username', '') or company.name
        parts = contact_name.split(maxsplit=1)
        ET.SubElement(contractor, _cml('Имя')).text = parts[0] if parts else company.name
        ET.SubElement(contractor, _cml('Фамилия')).text = parts[1] if len(parts) > 1 else ''

        address_node = ET.SubElement(contractor, _cml('АдресРегистрации'))
        address_text = company.legal_address or company.address or company.shipping_address or company.name
        ET.SubElement(address_node, _cml('Представление')).text = address_text
        contacts = ET.SubElement(address_node, _cml('Контакты'))
        if company.email:
            c = ET.SubElement(contacts, _cml('Контакт'))
            ET.SubElement(c, _cml('Тип')).text = 'Почта'
            ET.SubElement(c, _cml('Значение')).text = company.email
        if company.phone:
            c = ET.SubElement(contacts, _cml('Контакт'))
            ET.SubElement(c, _cml('Тип')).text = 'Телефон'
            ET.SubElement(c, _cml('Значение')).text = company.phone
        if contact_name:
            c = ET.SubElement(contacts, _cml('Контакт'))
            ET.SubElement(c, _cml('Тип')).text = 'Контактное лицо'
            ET.SubElement(c, _cml('Значение')).text = contact_name

        reps = ET.SubElement(contractor, _cml('Представители'))
        rep = ET.SubElement(reps, _cml('Представитель'))
        rep_contractor = ET.SubElement(rep, _cml('Контрагент'))
        ET.SubElement(rep_contractor, _cml('Отношение')).text = 'Контактное лицо'
        ET.SubElement(rep_contractor, _cml('Ид')).text = company_id
        ET.SubElement(rep_contractor, _cml('Наименование')).text = contact_name

        items = ET.SubElement(doc, _cml('Товары'))
        for item in order.items.all():
            item_node = ET.SubElement(items, _cml('Товар'))
            product_id = str(item.product.external_id or item.product.code or item.product_code_snapshot)
            ET.SubElement(item_node, _cml('Ид')).text = product_id
            ET.SubElement(item_node, _cml('Артикул')).text = item.product_code_snapshot or product_id
            ET.SubElement(item_node, _cml('Наименование')).text = item.product_name_snapshot
            base_unit = ET.SubElement(item_node, _cml('БазоваяЕдиница'), Код='796', НаименованиеПолное='Штука', МеждународноеСокращение='PCE')
            base_unit.text = item.product.unit or 'шт'
            ET.SubElement(item_node, _cml('ЦенаЗаЕдиницу')).text = f'{item.price:.2f}'
            ET.SubElement(item_node, _cml('Количество')).text = f'{item.qty:.3f}'
            ET.SubElement(item_node, _cml('Сумма')).text = f'{item.line_total:.2f}'

        reqs = ET.SubElement(doc, _cml('ЗначенияРеквизитов'))
        req = ET.SubElement(reqs, _cml('ЗначениеРеквизита'))
        ET.SubElement(req, _cml('Наименование')).text = 'Статус заказа'
        ET.SubElement(req, _cml('Значение')).text = 'Принят'
        req = ET.SubElement(reqs, _cml('ЗначениеРеквизита'))
        ET.SubElement(req, _cml('Наименование')).text = 'Метод оплаты'
        ET.SubElement(req, _cml('Значение')).text = 'Безналичный расчет'

        exported_orders.append(order)

    tree = ET.ElementTree(root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    checksum = _sha256(output_path)

    archive_path = _archive_output_path(output_path, profile, batch.code)
    archive_path.write_bytes(output_path.read_bytes())
    ExchangeArtifact.objects.create(batch=batch, kind='orders_xml', file_path=str(archive_path), checksum=checksum)

    for order in exported_orders:
        order.imported_to_erp = True
        order.erp_export_state = 'exported'
        order.exported_at = timezone.now()
        order.last_export_batch = batch
        order.last_export_hash = checksum
        order.locked_after_export = True
        order.erp_sync_error = ''
        order.save(update_fields=['imported_to_erp', 'erp_export_state', 'exported_at', 'last_export_batch', 'last_export_hash', 'locked_after_export', 'erp_sync_error'])
        register_order_status_event(
            order=order,
            new_status='exported',
            source='system',
            comment='Заказ выгружен в ERP.',
            notify=False,
        )

    batch.orders_count = len(exported_orders)
    batch.success_count = len(exported_orders)
    batch.error_count = len(skipped)
    batch.file_path = str(archive_path)
    batch.checksum = checksum
    batch.status = 'warning' if skipped and exported_orders else ('error' if skipped and not exported_orders else 'ok')
    batch.finished_at = timezone.now()
    batch.save(update_fields=['orders_count', 'success_count', 'error_count', 'file_path', 'checksum', 'status', 'finished_at'])

    ExchangeLog.objects.create(
        profile=profile,
        batch=batch,
        direction='export',
        source='CommerceML',
        file_name=output_path.name,
        status='warning' if skipped else 'ok',
        message=f'Экспортировано заказов: {len(exported_orders)}. Пропущено: {len(skipped)}.',
        payload_excerpt='; '.join(f'{o.site_number}: {", ".join(errs)}' for o, errs in skipped[:10]),
    )
    return ExportResult(path=output_path, batch=batch, exported_orders=exported_orders, skipped=skipped)
