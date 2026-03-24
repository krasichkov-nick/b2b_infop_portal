from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Бренд')),
                ('slug', models.SlugField(max_length=255, unique=True, verbose_name='Slug')),
            ],
            options={'verbose_name': 'Бренд', 'verbose_name_plural': 'Бренды', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.CharField(blank=True, max_length=128, null=True, unique=True, verbose_name='Внешний ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('slug', models.SlugField(max_length=255, unique=True, verbose_name='Slug')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='catalog.category', verbose_name='Родитель')),
            ],
            options={'verbose_name': 'Категория', 'verbose_name_plural': 'Категории', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='PriceType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=64, unique=True, verbose_name='Код')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('currency', models.CharField(default='RUB', max_length=16, verbose_name='Валюта')),
                ('is_default', models.BooleanField(default=False, verbose_name='По умолчанию')),
            ],
            options={'verbose_name': 'Тип цены', 'verbose_name_plural': 'Типы цен', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=128, unique=True, verbose_name='Код')),
                ('external_id', models.CharField(blank=True, db_index=True, max_length=128, null=True, verbose_name='Внешний ID')),
                ('barcode', models.CharField(blank=True, db_index=True, max_length=64, null=True, verbose_name='Штрихкод')),
                ('name', models.CharField(max_length=500, verbose_name='Наименование')),
                ('slug', models.SlugField(max_length=500, unique=True, verbose_name='Slug')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('unit', models.CharField(blank=True, max_length=32, verbose_name='Ед. изм.')),
                ('min_order_qty', models.DecimalField(decimal_places=3, default='1', max_digits=12, verbose_name='Мин. заказ')),
                ('multiplicity', models.DecimalField(decimal_places=3, default='1', max_digits=12, verbose_name='Кратность')),
                ('is_published', models.BooleanField(default=True, verbose_name='Опубликован')),
                ('stock_total', models.DecimalField(decimal_places=3, default='0', max_digits=14, verbose_name='Общий остаток')),
                ('image_main', models.CharField(blank=True, max_length=1024, verbose_name='Основное изображение')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('brand', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='catalog.brand', verbose_name='Бренд')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='catalog.category', verbose_name='Категория')),
            ],
            options={'verbose_name': 'Товар', 'verbose_name_plural': 'Товары', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_path', models.CharField(max_length=1024, verbose_name='Путь к файлу')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_main', models.BooleanField(default=False, verbose_name='Основное')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='catalog.product', verbose_name='Товар')),
            ],
            options={'verbose_name': 'Изображение товара', 'verbose_name_plural': 'Изображения товаров', 'ordering': ['sort_order', 'id']},
        ),
        migrations.CreateModel(
            name='ProductPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Цена')),
                ('valid_from', models.DateField(blank=True, null=True, verbose_name='Действует с')),
                ('valid_to', models.DateField(blank=True, null=True, verbose_name='Действует по')),
                ('price_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='catalog.pricetype', verbose_name='Тип цены')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='catalog.product', verbose_name='Товар')),
            ],
            options={'verbose_name': 'Цена товара', 'verbose_name_plural': 'Цены товаров', 'ordering': ['product__name', 'price_type__name'], 'unique_together': {('product', 'price_type')}},
        ),
        migrations.AddIndex(model_name='product', index=models.Index(fields=['code'], name='apps_catalo_code_9fe479_idx')),
        migrations.AddIndex(model_name='product', index=models.Index(fields=['barcode'], name='apps_catalo_barcode_d89544_idx')),
        migrations.AddIndex(model_name='product', index=models.Index(fields=['name'], name='apps_catalo_name_80ea41_idx')),
    ]
