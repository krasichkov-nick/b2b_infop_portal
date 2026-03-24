from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('catalog', '0001_initial'),
        ('customers', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_number', models.CharField(max_length=64, unique=True, verbose_name='Номер на сайте')),
                ('external_number', models.CharField(blank=True, max_length=64, verbose_name='Номер в ERP')),
                ('status', models.CharField(choices=[('draft', 'Черновик'), ('new', 'Новый'), ('processing', 'В обработке'), ('approved', 'Подтвержден'), ('cancelled', 'Отменен'), ('exported', 'Выгружен в ERP')], default='new', max_length=16, verbose_name='Статус')),
                ('currency', models.CharField(default='RUB', max_length=8, verbose_name='Валюта')),
                ('subtotal', models.DecimalField(decimal_places=2, default='0', max_digits=14, verbose_name='Сумма')),
                ('total', models.DecimalField(decimal_places=2, default='0', max_digits=14, verbose_name='Итого')),
                ('comment', models.TextField(blank=True, verbose_name='Комментарий')),
                ('imported_to_erp', models.BooleanField(default=False, verbose_name='Импортирован в ERP')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлен')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='customers.company', verbose_name='Компания')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={'verbose_name': 'Заказ', 'verbose_name_plural': 'Заказы', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_code_snapshot', models.CharField(max_length=128, verbose_name='Код товара')),
                ('product_name_snapshot', models.CharField(max_length=500, verbose_name='Название товара')),
                ('qty', models.DecimalField(decimal_places=3, max_digits=14, verbose_name='Количество')),
                ('price', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Цена')),
                ('line_total', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Сумма строки')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order', verbose_name='Заказ')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='catalog.product', verbose_name='Товар')),
            ],
            options={'verbose_name': 'Строка заказа', 'verbose_name_plural': 'Строки заказа'},
        ),
    ]
