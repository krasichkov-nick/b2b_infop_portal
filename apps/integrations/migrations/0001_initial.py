from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='ExchangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('direction', models.CharField(choices=[('import', 'Импорт'), ('export', 'Экспорт')], max_length=16, verbose_name='Направление')),
                ('source', models.CharField(max_length=255, verbose_name='Источник')),
                ('file_name', models.CharField(blank=True, max_length=500, verbose_name='Файл')),
                ('status', models.CharField(choices=[('ok', 'Успешно'), ('warning', 'Предупреждение'), ('error', 'Ошибка')], max_length=16, verbose_name='Статус')),
                ('message', models.TextField(verbose_name='Сообщение')),
                ('payload_excerpt', models.TextField(blank=True, verbose_name='Фрагмент')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
            ],
            options={'verbose_name': 'Лог обмена', 'verbose_name_plural': 'Логи обмена', 'ordering': ['-created_at']},
        ),
    ]
