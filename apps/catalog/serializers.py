from rest_framework import serializers
from .models import Category, Brand, Product, ProductPrice


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'external_id', 'name', 'slug', 'parent']


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug']


class ProductPriceSerializer(serializers.ModelSerializer):
    price_type = serializers.CharField(source='price_type.code', read_only=True)

    class Meta:
        model = ProductPrice
        fields = ['price_type', 'amount', 'valid_from', 'valid_to']


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    prices = ProductPriceSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'code', 'external_id', 'barcode', 'name', 'slug', 'description', 'unit',
            'min_order_qty', 'multiplicity', 'stock_total', 'image_main',
            'category', 'brand', 'prices',
        ]
