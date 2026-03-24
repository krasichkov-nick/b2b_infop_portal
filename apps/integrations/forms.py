from django import forms

from apps.integrations.models import IntegrationProfile


class ManualExportForm(forms.Form):
    profile = forms.ModelChoiceField(queryset=IntegrationProfile.objects.filter(is_active=True), label='Профиль')
    order_ids = forms.CharField(required=False, label='ID заказов через запятую')
    force = forms.BooleanField(required=False, label='Игнорировать блокировку и выгрузить принудительно')
    batch_comment = forms.CharField(required=False, label='Комментарий к пакету')

    def cleaned_order_ids(self):
        raw = (self.cleaned_data.get('order_ids') or '').strip()
        if not raw:
            return []
        return [int(x.strip()) for x in raw.split(',') if x.strip()]


class ManualStatusImportForm(forms.Form):
    profile = forms.ModelChoiceField(queryset=IntegrationProfile.objects.filter(is_active=True), label='Профиль')
    file = forms.FileField(label='Файл статусов (CSV/XML)')
