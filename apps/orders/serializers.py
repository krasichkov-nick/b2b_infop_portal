from rest_framework import serializers

from .models import Order, OrderItem
from .services import OrderValidationError, create_order_for_user


class OrderItemWriteSerializer(serializers.Serializer):
    product_code = serializers.CharField()
    qty = serializers.DecimalField(max_digits=14, decimal_places=3)


class OrderItemReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product_code_snapshot', 'product_name_snapshot', 'qty', 'price', 'line_total']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'site_number', 'status', 'currency', 'subtotal', 'total', 'comment', 'created_at', 'items']


class OrderCreateSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)
    items = OrderItemWriteSerializer(many=True)

    def create(self, validated_data):
        try:
            return create_order_for_user(
                user=self.context['request'].user,
                raw_items=validated_data['items'],
                comment=validated_data.get('comment', ''),
            )
        except OrderValidationError as exc:
            raise serializers.ValidationError(str(exc)) from exc
