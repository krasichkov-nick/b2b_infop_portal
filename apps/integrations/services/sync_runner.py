from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from django.utils import timezone

from apps.integrations.models import ExchangeLog, IntegrationProfile
from apps.integrations.services.commerce_ml import CommerceMLImporter
from apps.integrations.services.notifications import notify_sync_failure
from apps.integrations.services.order_export import export_orders_xml
from apps.integrations.services.status_import import OrderStatusImporter


@dataclass
class SyncSummary:
    imported_catalog: bool = False
    imported_offers: bool = False
    exported_orders: bool = False
    imported_statuses: bool = False


def run_sync_profile(profile: IntegrationProfile) -> SyncSummary:
    summary = SyncSummary()
    started = timezone.now()
    try:
        if profile.import_xml_path or profile.offers_xml_path:
            importer = CommerceMLImporter(
                import_xml=profile.import_xml_path or None,
                offers_xml=profile.offers_xml_path or None,
                images_dir=profile.images_dir_path or None,
                profile=profile,
            )
            importer.run()
            summary.imported_catalog = bool(profile.import_xml_path)
            summary.imported_offers = bool(profile.offers_xml_path)

        if profile.export_orders_path and profile.auto_export_enabled:
            export_orders_xml(profile.export_orders_path, only_new=profile.export_only_new, profile=profile)
            summary.exported_orders = True

        if profile.status_feed_path and profile.auto_status_import_enabled and Path(profile.status_feed_path).exists():
            OrderStatusImporter(profile.status_feed_path, profile=profile).run()
            summary.imported_statuses = True

        profile.last_run_at = started
        profile.last_success_at = timezone.now()
        profile.last_error = ''
        profile.save(update_fields=['last_run_at', 'last_success_at', 'last_error'])
        ExchangeLog.objects.create(
            profile=profile,
            direction='system',
            source='Sync runner',
            status='ok',
            message='Синхронизация завершена успешно.',
            started_at=started,
            finished_at=timezone.now(),
        )
        return summary
    except Exception as exc:
        profile.last_run_at = started
        profile.last_error = str(exc)
        profile.save(update_fields=['last_run_at', 'last_error'])
        ExchangeLog.objects.create(
            profile=profile,
            direction='system',
            source='Sync runner',
            status='error',
            message=str(exc),
            started_at=started,
            finished_at=timezone.now(),
        )
        notify_sync_failure(recipients=profile.notify_email_list, profile_name=profile.name, message=str(exc))
        raise
