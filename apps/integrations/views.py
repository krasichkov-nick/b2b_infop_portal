from __future__ import annotations

from pathlib import Path

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.integrations.forms import ManualExportForm, ManualStatusImportForm
from apps.integrations.models import ExchangeArtifact, ExchangeBatch, ExchangeLog, IntegrationProfile
from apps.integrations.services.order_export import export_orders_xml
from apps.integrations.services.status_import import OrderStatusImporter
from apps.orders.models import Order


@staff_member_required
def batches_list(request):
    batches = ExchangeBatch.objects.select_related('profile').all()[:200]
    return render(request, 'integrations/batches_list.html', {'batches': batches})


@staff_member_required
def batch_detail(request, pk: int):
    batch = get_object_or_404(ExchangeBatch.objects.select_related('profile').prefetch_related('artifacts', 'orders'), pk=pk)
    logs = ExchangeLog.objects.filter(batch=batch).select_related('profile')
    return render(request, 'integrations/batch_detail.html', {'batch': batch, 'logs': logs})


@staff_member_required
def batch_artifact_download(request, pk: int):
    artifact = get_object_or_404(ExchangeArtifact, pk=pk)
    path = Path(artifact.file_path)
    if not path.exists() or not path.is_file():
        raise Http404('Файл не найден.')
    return FileResponse(path.open('rb'), as_attachment=True, filename=path.name)


@staff_member_required
def integration_dashboard(request):
    context = {
        'profiles': IntegrationProfile.objects.all(),
        'last_batches': ExchangeBatch.objects.select_related('profile').all()[:20],
        'pending_orders': Order.objects.filter(erp_export_state__in=['new', 'validated']).count(),
        'exported_without_status': Order.objects.filter(erp_export_state='exported', erp_status_code='').count(),
        'recent_errors': ExchangeLog.objects.filter(status='error').select_related('profile', 'batch')[:20],
    }
    return render(request, 'integrations/dashboard.html', context)


@staff_member_required
def manual_actions(request):
    export_form = ManualExportForm(prefix='export')
    status_form = ManualStatusImportForm(prefix='status')

    if request.method == 'POST':
        if 'run_export' in request.POST:
            export_form = ManualExportForm(request.POST, prefix='export')
            if export_form.is_valid():
                profile = export_form.cleaned_data['profile']
                order_ids = export_form.cleaned_order_ids()
                result = export_orders_xml(
                    profile.export_orders_path or str(Path('media') / 'exchange' / 'orders.xml'),
                    only_new=profile.export_only_new,
                    profile=profile,
                    force=export_form.cleaned_data['force'],
                    order_ids=order_ids,
                    batch_comment=export_form.cleaned_data['batch_comment'],
                )
                messages.success(request, f'Экспорт завершен: {len(result.exported_orders)} заказов, batch={result.batch.code}.')
                return redirect('integrations:batch-detail', pk=result.batch.pk)
        elif 'run_status_import' in request.POST:
            status_form = ManualStatusImportForm(request.POST, request.FILES, prefix='status')
            if status_form.is_valid():
                profile = status_form.cleaned_data['profile']
                upload = status_form.cleaned_data['file']
                temp_dir = Path('media') / 'exchange' / 'uploads' / timezone.now().strftime('%Y%m%d')
                temp_dir.mkdir(parents=True, exist_ok=True)
                target = temp_dir / upload.name
                with target.open('wb') as fh:
                    for chunk in upload.chunks():
                        fh.write(chunk)
                stats = OrderStatusImporter(target, profile=profile).run()
                messages.success(request, f'Статусы импортированы: обновлено {stats.updated}, без совпадений {stats.unmatched}.')
                return redirect('integrations:status-imports')

    return render(request, 'integrations/manual.html', {'export_form': export_form, 'status_form': status_form})


@staff_member_required
def status_imports(request):
    batches = ExchangeBatch.objects.filter(direction='import_statuses').select_related('profile').all()[:200]
    return render(request, 'integrations/status_imports.html', {'batches': batches})


@staff_member_required
def unmatched_statuses(request):
    logs = ExchangeLog.objects.filter(direction='status').exclude(payload_excerpt='').select_related('profile', 'batch')[:200]
    return render(request, 'integrations/unmatched_statuses.html', {'logs': logs})
