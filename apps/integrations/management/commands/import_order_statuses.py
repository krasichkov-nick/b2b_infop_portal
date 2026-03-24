from django.core.management.base import BaseCommand
from apps.integrations.models import IntegrationProfile
from apps.integrations.services.status_import import OrderStatusImporter


class Command(BaseCommand):
    help = 'Импортирует статусы заказов из CSV/XML фида ERP.'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Путь к CSV или XML файлу статусов')
        parser.add_argument('--profile-code', dest='profile_code', help='Опциональный код профиля интеграции')

    def handle(self, *args, **options):
        profile = None
        if options.get('profile_code'):
            profile = IntegrationProfile.objects.filter(code=options['profile_code']).first()
        stats = OrderStatusImporter(options['file'], profile=profile).run()
        self.stdout.write(self.style.SUCCESS(
            f'Обработано={stats.processed}, обновлено={stats.updated}, пропущено={stats.skipped}, без совпадений={stats.unmatched}'
        ))
