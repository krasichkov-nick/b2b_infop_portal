from django.core.management.base import BaseCommand

from apps.integrations.services.order_validation import validate_order_for_export
from apps.orders.models import Order


class Command(BaseCommand):
    help = 'Проверяет заказы, готовые к выгрузке в ERP.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Проверять все заказы')

    def handle(self, *args, **options):
        qs = Order.objects.select_related('company', 'user').prefetch_related('items__product')
        if not options['all']:
            qs = qs.filter(erp_export_state__in=['new', 'validated'])
        ready = 0
        invalid = 0
        for order in qs.order_by('pk'):
            result = validate_order_for_export(order)
            if result.ok:
                ready += 1
                self.stdout.write(self.style.SUCCESS(f'OK {order.pk} {order.site_number}'))
            else:
                invalid += 1
                self.stdout.write(self.style.WARNING(f'BAD {order.pk} {order.site_number}: ' + '; '.join(result.errors)))
        self.stdout.write(self.style.SUCCESS(f'Готово к выгрузке: {ready}; проблемных: {invalid}'))
