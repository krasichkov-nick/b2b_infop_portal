from django.contrib import admin
from .models import Order, OrderItem, OrderStatusEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_code_snapshot', 'product_name_snapshot', 'qty', 'price', 'line_total')


class OrderStatusEventInline(admin.TabularInline):
    model = OrderStatusEvent
    extra = 0
    readonly_fields = (
        'previous_status', 'new_status', 'source', 'comment', 'external_number',
        'raw_status_code', 'raw_status_label', 'source_file', 'created_at', 'applied_at'
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'site_number', 'external_uid', 'company', 'status', 'erp_export_state', 'external_number',
        'total', 'locked_after_export', 'imported_to_erp', 'created_at'
    )
    list_filter = ('status', 'erp_export_state', 'locked_after_export', 'imported_to_erp')
    search_fields = ('site_number', 'external_uid', 'external_number', 'company__name', 'company__external_id')
    inlines = [OrderItemInline, OrderStatusEventInline]
    readonly_fields = ('exported_at', 'erp_updated_at', 'last_export_hash')


@admin.register(OrderStatusEvent)
class OrderStatusEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'order', 'previous_status', 'new_status', 'source', 'raw_status_code')
    list_filter = ('new_status', 'source')
    search_fields = ('order__site_number', 'comment', 'external_number', 'raw_status_code', 'raw_status_label')
