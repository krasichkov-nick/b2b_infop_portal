from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('catalog', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Компания')),
                ('external_id', models.CharField(blank=True, max_length=128, null=True, unique=True, verbose_name='Внешний ID')),
                ('tax_id', models.CharField(blank=True, max_length=32, verbose_name='ИНН/налоговый номер')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='Email')),
                ('phone', models.CharField(blank=True, max_length=64, verbose_name='Телефон')),
                ('address', models.CharField(blank=True, max_length=500, verbose_name='Адрес')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('min_order_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Минимальная сумма заказа')),
                ('price_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='catalog.pricetype', verbose_name='Тип цены')),
            ],
            options={'verbose_name': 'Компания', 'verbose_name_plural': 'Компании', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='CompanyUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('owner', 'Владелец'), ('manager', 'Менеджер'), ('buyer', 'Закупщик')], default='buyer', max_length=16, verbose_name='Роль')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='users', to='customers.company', verbose_name='Компания')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='company_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Пользователь компании', 'verbose_name_plural': 'Пользователи компаний'},
        ),
    ]
