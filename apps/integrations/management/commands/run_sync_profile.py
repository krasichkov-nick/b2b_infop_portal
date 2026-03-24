import time
from django.core.management.base import BaseCommand, CommandError
from apps.integrations.models import IntegrationProfile
from apps.integrations.services.sync_runner import run_sync_profile


class Command(BaseCommand):
    help = 'Запускает полный цикл синхронизации по профилю интеграции.'

    def add_arguments(self, parser):
        parser.add_argument('--code', required=True, help='Код профиля интеграции')
        parser.add_argument('--loop', action='store_true', help='Запускать бесконечным циклом')
        parser.add_argument('--interval', type=int, default=0, help='Интервал повтора в секундах (по умолчанию берется из профиля)')

    def handle(self, *args, **options):
        profile = IntegrationProfile.objects.filter(code=options['code']).first()
        if not profile:
            raise CommandError('Профиль интеграции не найден.')
        if not profile.is_active:
            raise CommandError('Профиль неактивен.')

        def one_run():
            summary = run_sync_profile(profile)
            self.stdout.write(self.style.SUCCESS(
                f'OK profile={profile.code} import_catalog={summary.imported_catalog} '
                f'import_offers={summary.imported_offers} export_orders={summary.exported_orders} '
                f'import_statuses={summary.imported_statuses}'
            ))

        one_run()
        if options['loop']:
            interval = options['interval'] or max(profile.run_every_minutes * 60, 30)
            while True:
                time.sleep(interval)
                one_run()
