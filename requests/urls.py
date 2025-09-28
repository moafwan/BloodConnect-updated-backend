from django.urls import path
from . import views

urlpatterns = [
    path('requests/pending/', views.pending_requests, name='pending-requests'),
    path('requests/<int:request_id>/approve/', views.approve_request, name='approve-request'),
    path('requests/<int:request_id>/reject/', views.reject_request, name='reject-request'),
    path('notifications/<int:notification_id>/respond/', views.donor_response, name='donor-response'),
    path('notifications/donor/', views.donor_notifications, name='donor-notifications'),
    path('test-email/', views.test_email, name='test-email'),
]