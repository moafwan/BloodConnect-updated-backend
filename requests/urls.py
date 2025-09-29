from django.urls import path
from . import views

urlpatterns = [
    path('pending/', views.pending_requests, name='pending-requests'),  # /api/requests/pending/
    path('<int:request_id>/approve/', views.approve_request, name='approve-request'),  # /api/requests/{id}/approve/
    path('<int:request_id>/reject/', views.reject_request, name='reject-request'),  # /api/requests/{id}/reject/
    path('notifications/<int:notification_id>/respond/', views.donor_response, name='donor-response'),  # /api/requests/notifications/{id}/respond/
    path('notifications/donor/', views.donor_notifications, name='donor-notifications'),  # /api/requests/notifications/donor/
    path('test-email/', views.test_email, name='test-email'),  # /api/requests/test-email/
]