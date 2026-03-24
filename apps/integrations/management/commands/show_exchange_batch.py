from django.core.management.base import BaseCommand, CommandError

from apps.integrations.models import ExchangeBatch


class Command(BaseCommand):
    help = 'Показывает детали пакета обмена.'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, required=True)

    def handle(self, *args, **options):
        batch = ExchangeBatch.objects.filter(pk=options['id']).prefetch_related('artifacts', 'orders').first()
        if not batch:
            raise CommandError('Пакет не найден.')
        self.stdout.write(f'Batch: {batch.code}')
        self.stdout.write(f'Direction: {batch.direction}')
        self.stdout.write(f'Status: {batch.status}')
        self.stdout.write(f'File: {batch.file_path}')
        self.stdout.write(f'Checksum: {batch.checksum}')
        self.stdout.write(f'Orders: {batch.orders_count}')
        for order in batch.orders.all():
            self.stdout.write(f' - {order.pk} {order.site_number} {order.external_uid}')
