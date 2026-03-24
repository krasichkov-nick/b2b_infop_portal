from django.core.management.base import BaseCommand
from apps.integrations.models import IntegrationProfile
from apps.integrations.services.order_export import export_orders_xml


class Command(BaseCommand):
    help = 'Экспортирует заказы сайта в orders.xml для импорта в Инфо-Предприятие.'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True, help='Куда сохранить orders.xml')
        parser.add_argument('--all', action='store_true', help='Экспортировать все заказы, а не только новые')
        parser.add_argument('--force', action='store_true', help='Принудительно выгрузить даже уже выгруженные заказы')
        parser.add_argument('--order-ids', nargs='*', type=int, help='Список ID заказов для точечной выгрузки')
        parser.add_argument('--profile-code', dest='profile_code', help='Опциональный код профиля интеграции')
        parser.add_argument('--batch-comment', default='', help='Комментарий к пакету обмена')

    def handle(self, *args, **options):
        profile = None
        if options.get('profile_code'):
            profile = IntegrationProfile.objects.filter(code=options['profile_code']).first()
        result = export_orders_xml(
            options['output'],
            only_new=not options['all'],
            profile=profile,
            force=options['force'],
            order_ids=options.get('order_ids') or None,
            batch_comment=options.get('batch_comment') or '',
        )
        self.stdout.write(self.style.SUCCESS(
            f'Файл создан: {result.path}; batch={result.batch.code}; экспортировано={len(result.exported_orders)}; пропущено={len(result.skipped)}'
        ))
