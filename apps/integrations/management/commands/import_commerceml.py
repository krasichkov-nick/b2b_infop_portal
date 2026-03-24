from django.core.management.base import BaseCommand
from apps.integrations.models import IntegrationProfile
from apps.integrations.services.commerce_ml import CommerceMLImporter


class Command(BaseCommand):
    help = 'Импортирует catalog import.xml и offers.xml из CommerceML в B2B-портал.'

    def add_arguments(self, parser):
        parser.add_argument('--import-xml', dest='import_xml', help='Путь к import.xml')
        parser.add_argument('--offers-xml', dest='offers_xml', help='Путь к offers.xml')
        parser.add_argument('--images-dir', dest='images_dir', help='Путь к каталогу import_files')
        parser.add_argument('--profile-code', dest='profile_code', help='Опциональный код профиля интеграции')

    def handle(self, *args, **options):
        profile = None
        if options.get('profile_code'):
            profile = IntegrationProfile.objects.filter(code=options['profile_code']).first()
        importer = CommerceMLImporter(
            import_xml=options.get('import_xml'),
            offers_xml=options.get('offers_xml'),
            images_dir=options.get('images_dir'),
            profile=profile,
        )
        stats = importer.run()
        self.stdout.write(self.style.SUCCESS(
            f'Готово: categories={stats.categories}, products={stats.products}, prices={stats.prices}, stocks={stats.stocks}, images={stats.images}'
        ))
