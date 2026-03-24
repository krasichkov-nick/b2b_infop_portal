from __future__ import annotations

from decimal import Decimal

from apps.catalog.models import Product
from apps.orders.services import get_product_price_for_company


class SessionCart:
    SESSION_KEY = 'b2b_cart'

    def __init__(self, request):
        self.request = request
        self.session = request.session
        self.data = self.session.get(self.SESSION_KEY, {})

    def save(self):
        self.session[self.SESSION_KEY] = self.data
        self.session.modified = True

    def clear(self):
        self.data = {}
        self.save()

    def set_item(self, product_code: str, qty: Decimal):
        self.data[product_code] = str(qty)
        self.save()

    def add(self, product_code: str, qty: Decimal, replace: bool = False):
        current = Decimal(self.data.get(product_code, '0'))
        self.data[product_code] = str(qty if replace else current + qty)
        self.save()

    def remove(self, product_code: str):
        self.data.pop(product_code, None)
        self.save()

    def raw_items(self):
        return [{'product_code': code, 'qty': qty} for code, qty in self.data.items()]

    def build_lines(self):
        profile = getattr(self.request.user, 'company_profile', None)
        company = profile.company if profile else None
        products = Product.objects.filter(code__in=list(self.data.keys()), is_published=True).select_related('category', 'brand')
        product_map = {p.code: p for p in products}
        lines = []
        total = Decimal('0')
        for code, qty_text in self.data.items():
            product = product_map.get(code)
            if not product:
                continue
            qty = Decimal(qty_text)
            price_obj = get_product_price_for_company(product, company)
            price = price_obj.amount if price_obj else Decimal('0')
            line_total = qty * price
            total += line_total
            lines.append({
                'product': product,
                'qty': qty,
                'price': price,
                'line_total': line_total,
            })
        return lines, total

    def count(self):
        return len(self.data)
