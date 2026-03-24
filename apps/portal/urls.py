from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.CatalogListView.as_view(), name='catalog'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('catalog/', views.CatalogListView.as_view(), name='catalog'),
    path('catalog/<str:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/<str:slug>/', views.cart_add, name='cart-add'),
    path('cart/remove/<str:product_code>/', views.cart_remove, name='cart-remove'),
    path('cart/clear/', views.cart_clear, name='cart-clear'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/repeat/', views.repeat_order, name='repeat-order'),
    path('upload-order/', views.upload_order, name='upload-order'),
    path('integrations/', views.integration_dashboard, name='integration-dashboard'),
    path('integrations/logs/', views.exchange_log_list, name='exchange-log-list'),
    path('images/<int:product_id>/', views.product_image, name='product-image-main'),
    path('images/<int:product_id>/<int:image_id>/', views.product_image, name='product-image'),
]
