from decimal import Decimal
from django.db import models
from django.urls import reverse


class Category(models.Model):
    external_id = models.CharField('Внешний ID', max_length=128, unique=True, blank=True, null=True)
    name = models.CharField('Название', max_length=255)
    slug = models.SlugField('Slug', max_length=255, unique=True)
    parent = models.ForeignKey('self', verbose_name='Родитель', on_delete=models.CASCADE, blank=True, null=True, related_name='children')
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField('Бренд', max_length=255, unique=True)
    slug = models.SlugField('Slug', max_length=255, unique=True)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    code = models.CharField('Код', max_length=128, unique=True)
    external_id = models.CharField('Внешний ID', max_length=128, blank=True, null=True, db_index=True)
    barcode = models.CharField('Штрихкод', max_length=64, blank=True, null=True, db_index=True)
    name = models.CharField('Наименование', max_length=500)
    slug = models.SlugField('Slug', max_length=500, unique=True)
    description = models.TextField('Описание', blank=True)
    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.SET_NULL, blank=True, null=True, related_name='products')
    brand = models.ForeignKey(Brand, verbose_name='Бренд', on_delete=models.SET_NULL, blank=True, null=True, related_name='products')
    unit = models.CharField('Ед. изм.', max_length=32, blank=True)
    min_order_qty = models.DecimalField('Мин. заказ', max_digits=12, decimal_places=3, default=Decimal('1'))
    multiplicity = models.DecimalField('Кратность', max_digits=12, decimal_places=3, default=Decimal('1'))
    is_published = models.BooleanField('Опубликован', default=True)
    stock_total = models.DecimalField('Общий остаток', max_digits=14, decimal_places=3, default=Decimal('0'))
    image_main = models.CharField('Основное изображение', max_length=1024, blank=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['barcode']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f'{self.code} — {self.name}'

    @property
    def main_image_url(self):
        if not self.image_main:
            return ''
        return reverse('portal:product-image-main', kwargs={'product_id': self.id})


class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name='Товар', on_delete=models.CASCADE, related_name='images')
    image_path = models.CharField('Путь к файлу', max_length=1024)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_main = models.BooleanField('Основное', default=False)

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.image_path


class PriceType(models.Model):
    code = models.CharField('Код', max_length=64, unique=True)
    name = models.CharField('Название', max_length=255)
    currency = models.CharField('Валюта', max_length=16, default='RUB')
    is_default = models.BooleanField('По умолчанию', default=False)

    class Meta:
        verbose_name = 'Тип цены'
        verbose_name_plural = 'Типы цен'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductPrice(models.Model):
    product = models.ForeignKey(Product, verbose_name='Товар', on_delete=models.CASCADE, related_name='prices')
    price_type = models.ForeignKey(PriceType, verbose_name='Тип цены', on_delete=models.CASCADE, related_name='prices')
    amount = models.DecimalField('Цена', max_digits=14, decimal_places=2)
    valid_from = models.DateField('Действует с', blank=True, null=True)
    valid_to = models.DateField('Действует по', blank=True, null=True)

    class Meta:
        verbose_name = 'Цена товара'
        verbose_name_plural = 'Цены товаров'
        unique_together = [('product', 'price_type')]
        ordering = ['product__name', 'price_type__name']

    def __str__(self):
        return f'{self.product.code} / {self.price_type.code} = {self.amount}'
