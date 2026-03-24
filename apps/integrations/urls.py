from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    path('', views.integration_dashboard, name='dashboard'),
    path('batches/', views.batches_list, name='batches-list'),
    path('batches/<int:pk>/', views.batch_detail, name='batch-detail'),
    path('artifacts/<int:pk>/download/', views.batch_artifact_download, name='artifact-download'),
    path('manual/', views.manual_actions, name='manual-actions'),
    path('status-imports/', views.status_imports, name='status-imports'),
    path('unmatched-statuses/', views.unmatched_statuses, name='unmatched-statuses'),
]
