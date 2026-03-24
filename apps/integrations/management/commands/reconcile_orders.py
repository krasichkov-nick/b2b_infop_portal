from django.core.management.base import BaseCommand

from apps.orders.models import Order


class Command(BaseCommand):
    help = 'Показывает проблемные заказы в контуре ERP.'

    def handle(self, *args, **options):
        exported_without_status = Order.objects.filter(erp_export_state='exported', erp_status_code='')
        missing_uid = Order.objects.filter(external_uid='')
        errors = Order.objects.exclude(erp_sync_error='')

        self.stdout.write(self.style.WARNING('Выгружены, но без статуса ERP:'))
        for order in exported_without_status[:200]:
            self.stdout.write(f' - {order.pk} {order.site_number}')
        self.stdout.write(self.style.WARNING('Без external_uid:'))
        for order in missing_uid[:200]:
            self.stdout.write(f' - {order.pk} {order.site_number}')
        self.stdout.write(self.style.WARNING('С ошибками ERP:'))
        for order in errors[:200]:
            self.stdout.write(f' - {order.pk} {order.site_number}: {order.erp_sync_error}')
