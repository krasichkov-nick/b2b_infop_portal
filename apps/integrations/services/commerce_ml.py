from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET
from django.db import transaction
from django.utils.text import slugify
from apps.catalog.models import Category, Product, ProductImage, ProductPrice, PriceType
from apps.integrations.models import ExchangeLog, IntegrationProfile


IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff', '.JPG', '.JPEG', '.PNG', '.WEBP', '.BMP', '.GIF', '.TIF', '.TIFF')


def strip_tag(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag


def child_text(node: ET.Element, *names: str, default: str = '') -> str:
    for child in list(node):
        if strip_tag(child.tag) in names:
            return (child.text or '').strip()
    return default


def find_child(node: ET.Element, *names: str) -> ET.Element | None:
    for child in list(node):
        if strip_tag(child.tag) in names:
            return child
    return None


def iter_children(node: ET.Element, *names: str):
    for child in list(node):
        if strip_tag(child.tag) in names:
            yield child


@dataclass
class ImportStats:
    categories: int = 0
    products: int = 0
    prices: int = 0
    stocks: int = 0
    images: int = 0


class CommerceMLImporter:
    def __init__(self, import_xml: str | Path | None = None, offers_xml: str | Path | None = None, images_dir: str | Path | None = None, profile: IntegrationProfile | None = None):
        self.import_xml = Path(import_xml) if import_xml else None
        self.offers_xml = Path(offers_xml) if offers_xml else None
        self.images_dir = Path(images_dir) if images_dir else None
        self.profile = profile
        self.stats = ImportStats()
        self.category_map: dict[str, Category] = {}
        self.product_map: dict[str, Product] = {}

    def _parse(self, path: Path) -> ET.Element:
        return ET.parse(path).getroot()

    def _category_slug(self, name: str, external_id: str) -> str:
        base = slugify(name, allow_unicode=True) or f'category-{external_id}'
        slug = base
        idx = 2
        while Category.objects.exclude(external_id=external_id).filter(slug=slug).exists():
            slug = f'{base}-{idx}'
            idx += 1
        return slug

    def _product_slug(self, name: str, code: str) -> str:
        base = slugify(name, allow_unicode=True) or f'product-{code}'
        slug = base
        idx = 2
        while Product.objects.exclude(code=code).filter(slug=slug).exists():
            slug = f'{base}-{idx}'
            idx += 1
        return slug

    def _group_ids_from_product(self, product_node: ET.Element) -> list[str]:
        ids: list[str] = []
        groups_node = find_child(product_node, 'Группы', 'Groups')
        if groups_node is not None:
            for item in list(groups_node):
                if strip_tag(item.tag) in {'Ид', 'Id'}:
                    value = (item.text or '').strip()
                    if value:
                        ids.append(value)
        direct_group = child_text(product_node, 'Группа', 'Group')
        if direct_group and direct_group not in ids:
            ids.append(direct_group)
        return ids

    def _import_categories(self, root: ET.Element):
        classifier = None
        for node in root.iter():
            if strip_tag(node.tag) in {'Классификатор', 'Classifier'}:
                classifier = node
                break
        if classifier is None:
            return
        groups_root = find_child(classifier, 'Группы', 'Groups')
        if groups_root is None:
            return

        def walk(group_node: ET.Element, parent: Category | None = None):
            external_id = child_text(group_node, 'Ид', 'Id', default='')
            name = child_text(group_node, 'Наименование', 'Name', default='Без категории')
            if external_id:
                category, created = Category.objects.get_or_create(
                    external_id=external_id,
                    defaults={
                        'name': name,
                        'slug': self._category_slug(name, external_id),
                        'parent': parent,
                        'is_active': True,
                    },
                )
            else:
                category, created = Category.objects.get_or_create(
                    slug=self._category_slug(name, name),
                    defaults={
                        'name': name,
                        'parent': parent,
                        'is_active': True,
                    },
                )
            changed = False
            if category.name != name:
                category.name = name
                changed = True
            if category.parent_id != (parent.id if parent else None):
                category.parent = parent
                changed = True
            if not category.is_active:
                category.is_active = True
                changed = True
            if changed:
                category.save()
            if external_id:
                self.category_map[external_id] = category
            if created:
                self.stats.categories += 1
            subgroups = find_child(group_node, 'Группы', 'Groups')
            if subgroups is not None:
                for subgroup in iter_children(subgroups, 'Группа', 'Group'):
                    walk(subgroup, category)

        for group in iter_children(groups_root, 'Группа', 'Group'):
            walk(group)

    def _resolve_image_candidates(self, product: Product, product_node: ET.Element) -> list[str]:
        explicit_paths = [(img.text or '').strip() for img in iter_children(product_node, 'Картинка', 'Picture') if (img.text or '').strip()]
        candidates: list[str] = []
        if explicit_paths:
            for rel_path in explicit_paths:
                p = Path(rel_path)
                if self.images_dir and not p.is_absolute():
                    full = (self.images_dir / rel_path).resolve()
                else:
                    full = p.resolve() if p.is_absolute() else p
                if full.exists():
                    candidates.append(str(full))
        if candidates:
            return candidates
        if not self.images_dir or not self.images_dir.exists():
            return []
        stems = [s for s in {product.code, product.external_id, product.barcode} if s]
        found: list[str] = []
        for stem in stems:
            for ext in IMAGE_EXTENSIONS:
                p = self.images_dir / f'{stem}{ext}'
                if p.exists():
                    found.append(str(p.resolve()))
        # unique, preserve order
        return list(dict.fromkeys(found))

    def _assign_images(self, product: Product, product_node: ET.Element):
        images = self._resolve_image_candidates(product, product_node)
        if not images:
            return
        existing = list(ProductImage.objects.filter(product=product).order_by('sort_order', 'id').values_list('image_path', flat=True))
        if existing == images and product.image_main == images[0]:
            return
        ProductImage.objects.filter(product=product).delete()
        for idx, path in enumerate(images):
            ProductImage.objects.create(product=product, image_path=path, sort_order=idx, is_main=(idx == 0))
            self.stats.images += 1
        if product.image_main != images[0]:
            product.image_main = images[0]
            product.save(update_fields=['image_main'])

    def _import_products(self, root: ET.Element):
        catalog = None
        for node in root.iter():
            if strip_tag(node.tag) in {'Каталог', 'Catalog'}:
                catalog = node
                break
        if catalog is None:
            return
        goods_root = find_child(catalog, 'Товары', 'Products')
        if goods_root is None:
            return
        for product_node in iter_children(goods_root, 'Товар', 'Product'):
            external_id = child_text(product_node, 'Ид', 'Id')
            code = child_text(product_node, 'Артикул', 'Code') or external_id
            name = child_text(product_node, 'Наименование', 'Name') or code
            barcode = child_text(product_node, 'Штрихкод', 'Barcode')
            description = child_text(product_node, 'Описание', 'Description')
            base_unit_node = find_child(product_node, 'БазоваяЕдиница', 'BaseUnit')
            unit = ''
            if base_unit_node is not None:
                unit = (base_unit_node.text or '').strip() or base_unit_node.attrib.get('НаименованиеКраткое', '') or base_unit_node.attrib.get('НаименованиеПолное', '') or base_unit_node.attrib.get('ShortName', '') or base_unit_node.attrib.get('FullName', '')
            group_ids = self._group_ids_from_product(product_node)
            category = self.category_map.get(group_ids[0]) if group_ids else None
            product, created = Product.objects.get_or_create(
                code=code,
                defaults={
                    'external_id': external_id,
                    'barcode': barcode,
                    'name': name,
                    'slug': self._product_slug(name, code),
                    'description': description,
                    'category': category,
                    'unit': unit,
                    'is_published': True,
                },
            )
            changed = False
            updates = {
                'external_id': external_id,
                'barcode': barcode,
                'name': name,
                'description': description,
                'category': category,
                'unit': unit,
                'is_published': True,
            }
            for field, value in updates.items():
                if getattr(product, field) != value:
                    setattr(product, field, value)
                    changed = True
            if changed:
                product.save()
            self.product_map[external_id or code] = product
            self.product_map[code] = product
            if barcode:
                self.product_map[barcode] = product
            if created:
                self.stats.products += 1
            self._assign_images(product, product_node)

    def _import_offers(self, root: ET.Element):
        package = None
        for node in root.iter():
            if strip_tag(node.tag) in {'ПакетПредложений', 'OffersPackage'}:
                package = node
                break
        if package is None:
            return

        price_type_map: dict[str, PriceType] = {}
        price_types_root = find_child(package, 'ТипыЦен', 'PriceTypes')
        if price_types_root is not None:
            for pt_node in iter_children(price_types_root, 'ТипЦены', 'PriceType'):
                pt_id = child_text(pt_node, 'Ид', 'Id') or child_text(pt_node, 'Наименование', 'Name')
                pt_name = child_text(pt_node, 'Наименование', 'Name') or pt_id
                currency = child_text(pt_node, 'Валюта', 'Currency', default='RUB') or 'RUB'
                pt, _ = PriceType.objects.get_or_create(code=pt_id, defaults={'name': pt_name, 'currency': currency})
                changed = False
                if pt.name != pt_name:
                    pt.name = pt_name
                    changed = True
                if pt.currency != currency:
                    pt.currency = currency
                    changed = True
                if changed:
                    pt.save(update_fields=['name', 'currency'])
                price_type_map[pt_id] = pt
        if price_type_map:
            defaults = PriceType.objects.filter(is_default=True)
            if not defaults.exists():
                first = next(iter(price_type_map.values()))
                first.is_default = True
                first.save(update_fields=['is_default'])

        offers_root = find_child(package, 'Предложения', 'Offers')
        if offers_root is None:
            return
        for offer_node in iter_children(offers_root, 'Предложение', 'Offer'):
            offer_id = child_text(offer_node, 'Ид', 'Id')
            code = child_text(offer_node, 'Артикул', 'Code') or offer_id
            barcode = child_text(offer_node, 'Штрихкод', 'Barcode')
            product = (
                self.product_map.get(code)
                or self.product_map.get(offer_id)
                or (self.product_map.get(barcode) if barcode else None)
                or Product.objects.filter(code=code).first()
                or Product.objects.filter(external_id=offer_id).first()
                or (Product.objects.filter(barcode=barcode).first() if barcode else None)
            )
            if not product:
                continue
            qty_text = child_text(offer_node, 'Количество', 'Quantity', default='0').replace(',', '.')
            try:
                qty = Decimal(qty_text)
            except Exception:
                qty = Decimal('0')
            if product.stock_total != qty:
                product.stock_total = qty
                product.save(update_fields=['stock_total'])
                self.stats.stocks += 1

            prices_root = find_child(offer_node, 'Цены', 'Prices')
            if prices_root is not None:
                for price_node in iter_children(prices_root, 'Цена', 'Price'):
                    pt_id = child_text(price_node, 'ИдТипаЦены', 'PriceTypeId')
                    amount_text = child_text(price_node, 'ЦенаЗаЕдиницу', 'PricePerUnit', default='0').replace(',', '.')
                    valid_from = child_text(package, 'ДействительноС', 'ValidFrom') or None
                    valid_to = child_text(package, 'ДействительноДо', 'ValidTo') or None
                    try:
                        amount = Decimal(amount_text)
                    except Exception:
                        continue
                    price_type = price_type_map.get(pt_id)
                    if not price_type:
                        price_type, _ = PriceType.objects.get_or_create(code=pt_id or 'default', defaults={'name': pt_id or 'Default', 'currency': 'RUB'})
                        price_type_map[price_type.code] = price_type
                    ProductPrice.objects.update_or_create(
                        product=product,
                        price_type=price_type,
                        defaults={'amount': amount, 'valid_from': valid_from, 'valid_to': valid_to},
                    )
                    self.stats.prices += 1

    @transaction.atomic
    def run(self):
        if self.import_xml:
            import_root = self._parse(self.import_xml)
            self._import_categories(import_root)
            self._import_products(import_root)
            ExchangeLog.objects.create(
                profile=self.profile,
                direction='import',
                source='CommerceML',
                file_name=self.import_xml.name,
                status='ok',
                message=f'Импортирован catalog: categories={self.stats.categories}, products={self.stats.products}, images={self.stats.images}',
            )
        if self.offers_xml:
            offers_root = self._parse(self.offers_xml)
            self._import_offers(offers_root)
            ExchangeLog.objects.create(
                profile=self.profile,
                direction='import',
                source='CommerceML',
                file_name=self.offers_xml.name,
                status='ok',
                message=f'Импортированы offers: prices={self.stats.prices}, stocks={self.stats.stocks}',
            )
        return self.stats
