from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import xml.etree.ElementTree as ET

from django.utils import timezone

from apps.integrations.models import ERPStatusMapping, ExchangeArtifact, ExchangeBatch, ExchangeLog, IntegrationProfile
from apps.orders.models import Order
from apps.orders.services import register_order_status_event


def strip_tag(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag


def child_text(node: ET.Element, *names: str, default: str = '') -> str:
    for child in list(node):
        if strip_tag(child.tag) in names:
            return (child.text or '').strip()
    return default


@dataclass
class StatusImportStats:
    processed: int = 0
    updated: int = 0
    skipped: int = 0
    unmatched: int = 0


class OrderStatusImporter:
    def __init__(self, status_path: str | Path, profile: IntegrationProfile | None = None):
        self.path = Path(status_path)
        self.profile = profile
        self.stats = StatusImportStats()
        self.batch: ExchangeBatch | None = None
        self.artifact: ExchangeArtifact | None = None

    def _sha256(self) -> str:
        h = hashlib.sha256()
        with self.path.open('rb') as fh:
            for chunk in iter(lambda: fh.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def _mapping(self, status: str) -> tuple[str, str]:
        raw = (status or '').strip()
        key = raw.lower()
        m = ERPStatusMapping.objects.filter(source_code__iexact=key).first() or ERPStatusMapping.objects.filter(source_label__iexact=raw).first()
        if m:
            return m.internal_status, raw
        fallback = {
            'new': 'new',
            'новый': 'new',

            'processing': 'processing',
            'в обработке': 'processing',

            'approved': 'approved',
            'подтвержден': 'approved',
            'подтверждён': 'approved',
            'зарезервирован': 'approved',

            'exported': 'exported',
            'выгружен': 'exported',
            'выгружен в erp': 'exported',

            'invoiced': 'invoiced',
            'счет': 'invoiced',
            'счёт': 'invoiced',
            'выставлен счет': 'invoiced',
            'выставлен счёт': 'invoiced',
            'выписан': 'invoiced',

            'paid': 'paid',
            'оплачен': 'paid',

            'overdue': 'overdue',
            'просрочен': 'overdue',

            'shipped': 'shipped',
            'отгружен': 'shipped',

            'completed': 'completed',
            'завершен': 'completed',
            'завершён': 'completed',
            'закрыт': 'completed',

            'cancelled': 'cancelled',
            'отменен': 'cancelled',
            'отменён': 'cancelled',
        }
        return fallback.get(key, ''), raw

    def _find_order(self, external_uid: str = '', site_number: str = '', external_number: str = '') -> Order | None:
        if external_uid:
            order = Order.objects.filter(external_uid=external_uid).first()
            if order:
                return order
        if site_number:
            order = Order.objects.filter(site_number=site_number).first()
            if order:
                return order
        if external_number:
            order = Order.objects.filter(external_number=external_number).first()
            if order:
                return order
        return None

    def _latest_key(self, external_uid: str, site_number: str, external_number: str) -> str:
        return external_uid or site_number or f'erp:{external_number}'

    def _apply_record(self, *, external_uid: str = '', site_number: str = '', external_number: str = '', status: str = '', comment: str = '', payload_excerpt: str = ''):
        self.stats.processed += 1
        normalized_status, raw_label = self._mapping(status)
        order = self._find_order(external_uid=external_uid, site_number=site_number, external_number=external_number)
        if not order:
            self.stats.unmatched += 1
            self.stats.skipped += 1
            return
        if not normalized_status:
            self.stats.skipped += 1
            order.erp_sync_error = f'Неизвестный статус ERP: {status}'
            order.save(update_fields=['erp_sync_error'])
            return
        latest_event = order.status_events.order_by('-created_at').first()
        if latest_event and latest_event.new_status == normalized_status and latest_event.raw_status_label == raw_label:
            self.stats.skipped += 1
            return
        order.erp_last_payload_ref = self.artifact
        order.save(update_fields=['erp_last_payload_ref'])
        register_order_status_event(
            order=order,
            new_status=normalized_status,
            source='erp',
            comment=comment,
            external_number=external_number,
            raw_status_code=status,
            raw_status_label=raw_label,
            source_file=self.path.name,
            payload_excerpt=payload_excerpt[:1000],
            notify=True,
        )
        self.stats.updated += 1

    def _collect_csv_records(self):
        latest = {}
        with self.path.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                normalized = {str(k).strip().lower(): v for k, v in row.items()}
                external_uid = (normalized.get('external_uid') or normalized.get('uid') or normalized.get('ид') or '').strip()
                site_number = (normalized.get('site_number') or normalized.get('номер_сайта') or normalized.get('site') or '').strip()
                external_number = (normalized.get('external_number') or normalized.get('номер_erp') or normalized.get('erp_number') or normalized.get('erp_document_number') or '').strip()
                key = self._latest_key(external_uid, site_number, external_number)
                latest[key] = {
                    'external_uid': external_uid,
                    'site_number': site_number,
                    'external_number': external_number,
                    'status': (normalized.get('status') or normalized.get('статус') or normalized.get('erp_status_label') or '').strip(),
                    'comment': (normalized.get('comment') or normalized.get('комментарий') or '').strip(),
                    'payload_excerpt': str(row),
                }
        return latest.values()

    def _extract_requisite_status(self, doc: ET.Element) -> tuple[str, str]:
        requisites = [child for child in list(doc) if strip_tag(child.tag) in {'ЗначенияРеквизитов', 'RequisiteValues'}]
        status, comment = '', ''
        for req_root in requisites:
            for req in list(req_root):
                if strip_tag(req.tag) not in {'ЗначениеРеквизита', 'RequisiteValue'}:
                    continue
                name = child_text(req, 'Наименование', 'Name').strip().lower()
                value = child_text(req, 'Значение', 'Value').strip()
                if name in {'статус', 'status', 'состояние', 'статус заказа'} and not status:
                    status = value
                if name in {'комментарий', 'comment'} and not comment:
                    comment = value
        return status, comment

    def _collect_xml_records(self):
        latest = {}
        root = ET.parse(self.path).getroot()
        for doc in root.iter():
            if strip_tag(doc.tag) not in {'Документ', 'Document'}:
                continue
            external_uid = child_text(doc, 'Ид', 'Id')
            site_number = child_text(doc, 'Номер', 'Number')
            external_number = child_text(doc, 'НомерERP', 'ExternalNumber') or site_number
            status = child_text(doc, 'Статус', 'Status')
            comment = child_text(doc, 'Комментарий', 'Comment')
            req_status, req_comment = self._extract_requisite_status(doc)
            latest[self._latest_key(external_uid, site_number, external_number)] = {
                'external_uid': external_uid,
                'site_number': site_number,
                'external_number': external_number,
                'status': status or req_status,
                'comment': comment or req_comment,
                'payload_excerpt': ET.tostring(doc, encoding='unicode'),
            }
        return latest.values()

    def run(self) -> StatusImportStats:
        self.batch = ExchangeBatch.objects.create(
            code=timezone.now().strftime('STS%Y%m%d%H%M%S%f'),
            direction='import_statuses',
            profile=self.profile,
            status='created',
            started_at=timezone.now(),
        )
        checksum = self._sha256()
        self.artifact = ExchangeArtifact.objects.create(
            batch=self.batch,
            kind='status_csv' if self.path.suffix.lower() == '.csv' else 'status_xml',
            file_path=str(self.path),
            checksum=checksum,
        )
        records = self._collect_csv_records() if self.path.suffix.lower() == '.csv' else self._collect_xml_records()
        for record in records:
            self._apply_record(**record)
        self.batch.orders_count = self.stats.processed
        self.batch.success_count = self.stats.updated
        self.batch.error_count = self.stats.unmatched
        self.batch.file_path = str(self.path)
        self.batch.checksum = checksum
        self.batch.status = 'warning' if self.stats.unmatched else 'ok'
        self.batch.finished_at = timezone.now()
        self.batch.save(update_fields=['orders_count', 'success_count', 'error_count', 'file_path', 'checksum', 'status', 'finished_at'])
        ExchangeLog.objects.create(
            profile=self.profile,
            batch=self.batch,
            direction='status',
            source='ERP status feed',
            file_name=self.path.name,
            status='warning' if self.stats.unmatched else 'ok',
            message=f'Обработано={self.stats.processed}, обновлено={self.stats.updated}, пропущено={self.stats.skipped}, без совпадений={self.stats.unmatched}',
        )
        return self.stats
