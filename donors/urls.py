from django.urls import path
from . import views

urlpatterns = [
    path('', views.donor_list, name='donor-list'),  # /api/donors/
    path('<int:donor_id>/', views.donor_detail, name='donor-detail'),  # /api/donors/{id}/
    path('donor/profile/', views.donor_profile, name='donor-profile'),  # /api/donors/donor/profile/
    path('donor/donation-history/', views.donation_history, name='donation-history'),  # /api/donors/donor/donation-history/
]