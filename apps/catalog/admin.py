from django.contrib import admin
from .models import Category, Brand, Product, ProductImage, PriceType, ProductPrice


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'barcode', 'category', 'stock_total', 'is_published')
    list_filter = ('is_published', 'category', 'brand')
    search_fields = ('code', 'barcode', 'name')
    inlines = [ProductImageInline, ProductPriceInline]


admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(PriceType)
