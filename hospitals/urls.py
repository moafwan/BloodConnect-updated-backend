from django.urls import path
from . import views

urlpatterns = [
    path('blood-requests/create/', views.create_blood_request, name='create-blood-request'),
    path('blood-requests/', views.hospital_requests, name='hospital-requests'),
    path('profile/', views.hospital_profile, name='hospital-profile'),  # NEW
    path('stats/', views.hospital_stats, name='hospital-stats'),
    path('request-stats/', views.request_stats, name='request-stats'),
]