from django.contrib import admin
from .models import ERPStatusMapping, ExchangeArtifact, ExchangeBatch, ExchangeLog, IntegrationProfile


@admin.register(IntegrationProfile)
class IntegrationProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'run_every_minutes', 'last_success_at', 'last_error_short')
    list_filter = ('is_active', 'auto_export_enabled', 'auto_status_import_enabled')
    search_fields = ('name', 'code', 'notify_emails')

    def last_error_short(self, obj):
        return (obj.last_error or '')[:80]


@admin.register(ExchangeBatch)
class ExchangeBatchAdmin(admin.ModelAdmin):
    list_display = ('code', 'direction', 'profile', 'status', 'orders_count', 'success_count', 'error_count', 'created_at')
    list_filter = ('direction', 'status', 'profile')
    search_fields = ('code', 'comment', 'file_path', 'checksum')


@admin.register(ExchangeArtifact)
class ExchangeArtifactAdmin(admin.ModelAdmin):
    list_display = ('batch', 'kind', 'file_path', 'created_at')
    list_filter = ('kind',)
    search_fields = ('batch__code', 'file_path', 'checksum')


@admin.register(ERPStatusMapping)
class ERPStatusMappingAdmin(admin.ModelAdmin):
    list_display = ('source_code', 'source_label', 'internal_status', 'is_terminal', 'notify_customer')
    list_filter = ('internal_status', 'is_terminal', 'notify_customer')
    search_fields = ('source_code', 'source_label')


@admin.register(ExchangeLog)
class ExchangeLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'profile', 'batch', 'direction', 'source', 'file_name', 'status')
    list_filter = ('direction', 'status', 'source', 'profile')
    search_fields = ('file_name', 'message', 'payload_excerpt', 'batch__code')
