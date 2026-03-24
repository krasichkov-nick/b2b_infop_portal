from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import DetailView, ListView, TemplateView

from apps.catalog.models import Brand, Category, Product
from apps.integrations.models import ExchangeLog, IntegrationProfile
from apps.orders.models import Order
from apps.orders.services import OrderValidationError, create_order_for_user, get_product_price_for_company
from .cart import SessionCart
from .forms import CartAddForm, CheckoutForm, OrderUploadForm, UploadedOrderParser


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, 'company_profile', None)
        company = profile.company if profile else None
        recent_orders = Order.objects.filter(company=company).prefetch_related('items')[:5] if company else []
        ctx.update({
            'company': company,
            'recent_orders': recent_orders,
            'draft_count': Order.objects.filter(company=company, status='draft').count() if company else 0,
            'new_count': Order.objects.filter(company=company, status='new').count() if company else 0,
            'processing_count': Order.objects.filter(company=company, status='processing').count() if company else 0,
            'completed_count': Order.objects.filter(company=company, status='completed').count() if company else 0,
        })
        return ctx


class CatalogListView(ListView):
    template_name = 'portal/catalog_list.html'
    context_object_name = 'products'
    paginate_by = 24

    def get_queryset(self):
        qs = Product.objects.filter(is_published=True).select_related('category', 'brand').prefetch_related('prices')
        q = self.request.GET.get('q', '').strip()
        category = self.request.GET.get('category', '').strip()
        brand = self.request.GET.get('brand', '').strip()
        availability = self.request.GET.get('availability', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(barcode__icontains=q))
        if category:
            qs = qs.filter(category__slug=category)
        if brand:
            qs = qs.filter(brand__slug=brand)
        if availability == 'in_stock':
            qs = qs.filter(stock_total__gt=0)
        return qs.order_by('name').distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, 'company_profile', None)
        company = profile.company if profile else None
        ctx['categories'] = Category.objects.filter(is_active=True)
        ctx['brands'] = Brand.objects.all()
        ctx['company'] = company
        ctx['query'] = self.request.GET.get('q', '')
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['selected_brand'] = self.request.GET.get('brand', '')
        ctx['selected_availability'] = self.request.GET.get('availability', '')
        return ctx


class ProductDetailView(DetailView):
    template_name = 'portal/product_detail.html'
    model = Product
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.filter(is_published=True).select_related('category', 'brand').prefetch_related('prices', 'images')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = CartAddForm(initial={'qty': self.object.min_order_qty})
        profile = getattr(self.request.user, 'company_profile', None)
        company = profile.company if profile else None
        price_obj = get_product_price_for_company(self.object, company)
        ctx['current_price'] = price_obj.amount if price_obj else None
        return ctx


@login_required
def cart_detail(request):
    cart = SessionCart(request)
    lines, total = cart.build_lines()
    return render(request, 'portal/cart_detail.html', {
        'cart_lines': lines,
        'cart_total': total,
        'checkout_form': CheckoutForm(),
    })


@login_required
def cart_add(request, slug):
    product = get_object_or_404(Product, slug=slug, is_published=True)
    form = CartAddForm(request.POST or None)
    if request.method != 'POST' or not form.is_valid():
        return HttpResponseBadRequest('Некорректные данные.')
    cart = SessionCart(request)
    cart.add(product.code, form.cleaned_data['qty'], replace=form.cleaned_data['replace'])
    messages.success(request, f'Товар «{product.name}» добавлен в корзину.')
    return redirect(request.POST.get('next') or reverse('portal:cart'))


@login_required
def cart_remove(request, product_code):
    cart = SessionCart(request)
    cart.remove(product_code)
    messages.info(request, 'Позиция удалена из корзины.')
    return redirect('portal:cart')


@login_required
def cart_clear(request):
    SessionCart(request).clear()
    messages.info(request, 'Корзина очищена.')
    return redirect('portal:cart')


@login_required
def checkout(request):
    cart = SessionCart(request)
    lines, total = cart.build_lines()
    if not lines:
        messages.warning(request, 'Корзина пустая.')
        return redirect('portal:catalog')

    form = CheckoutForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            order = create_order_for_user(user=request.user, raw_items=cart.raw_items(), comment=form.cleaned_data['comment'])
        except OrderValidationError as exc:
            messages.error(request, str(exc))
        else:
            cart.clear()
            messages.success(request, f'Заказ {order.site_number} создан.')
            return redirect('portal:order-detail', pk=order.pk)

    return render(request, 'portal/checkout.html', {
        'cart_lines': lines,
        'cart_total': total,
        'form': form,
    })


class OrderListView(LoginRequiredMixin, ListView):
    template_name = 'portal/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        profile = getattr(self.request.user, 'company_profile', None)
        company = profile.company if profile else None
        return Order.objects.filter(company=company).prefetch_related('items', 'status_events')


class OrderDetailView(LoginRequiredMixin, DetailView):
    template_name = 'portal/order_detail.html'
    model = Order
    context_object_name = 'order'

    def get_queryset(self):
        profile = getattr(self.request.user, 'company_profile', None)
        company = profile.company if profile else None
        return Order.objects.filter(company=company).prefetch_related('items__product', 'status_events')


@login_required
def repeat_order(request, pk):
    profile = getattr(request.user, 'company_profile', None)
    company = profile.company if profile else None
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=pk, company=company)
    cart = SessionCart(request)
    cart.clear()
    for item in order.items.all():
        cart.set_item(item.product.code, item.qty)
    messages.success(request, f'Позиции из заказа {order.site_number} загружены в корзину.')
    return redirect('portal:cart')


@login_required
def upload_order(request):
    form = OrderUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        try:
            rows = UploadedOrderParser.parse(form.cleaned_data['file'])
        except Exception as exc:
            form.add_error('file', str(exc))
        else:
            cart = SessionCart(request)
            if form.cleaned_data['mode'] == 'replace':
                cart.clear()
            for row in rows:
                cart.add(row.product_code, row.qty, replace=False)
            messages.success(request, f'В корзину загружено {len(rows)} строк из файла.')
            return redirect('portal:cart')
    return render(request, 'portal/upload_order.html', {'form': form})


@login_required
def product_image(request, product_id: int, image_id: int | None = None):
    product = get_object_or_404(Product.objects.prefetch_related('images'), pk=product_id)
    path = product.image_main
    if image_id is not None:
        image = product.images.filter(pk=image_id).first()
        if image:
            path = image.image_path
    if not path:
        raise Http404('Изображение не найдено.')
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise Http404('Файл изображения не найден на диске.')
    response = FileResponse(file_path.open('rb'))
    response['Content-Disposition'] = f'inline; filename="{quote(file_path.name)}"'
    return response


@staff_member_required
def integration_dashboard(request):
    profiles = IntegrationProfile.objects.all().prefetch_related('logs')
    logs = ExchangeLog.objects.select_related('profile')[:40]
    return render(request, 'portal/integration_dashboard.html', {
        'profiles': profiles,
        'logs': logs,
        'pending_orders': Order.objects.filter(imported_to_erp=False).count(),
        'processing_orders': Order.objects.filter(status='processing').count(),
    })


@staff_member_required
def exchange_log_list(request):
    qs = ExchangeLog.objects.select_related('profile').all()
    status = request.GET.get('status', '').strip()
    direction = request.GET.get('direction', '').strip()
    if status:
        qs = qs.filter(status=status)
    if direction:
        qs = qs.filter(direction=direction)
    return render(request, 'portal/exchange_log_list.html', {
        'logs': qs[:200],
        'status_filter': status,
        'direction_filter': direction,
    })
