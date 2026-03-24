from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.catalog.api import CategoryViewSet, BrandViewSet, ProductViewSet
from apps.orders.api import OrderViewSet
from apps.customers.api import CompanyMeAPIView

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('brands', BrandViewSet, basename='brand')
router.register('products', ProductViewSet, basename='product')
router.register('orders', OrderViewSet, basename='order')

urlpatterns = [
    path('integrations/', include('apps.integrations.urls')),
    path('', include('apps.portal.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('api/me/company/', CompanyMeAPIView.as_view(), name='company-me'),
    path('api/', include(router.urls)),
]
