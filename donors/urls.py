from django.urls import path
from . import views

urlpatterns = [
    path('donors/', views.donor_list, name='donor-list'),
    path('donors/<int:donor_id>/', views.donor_detail, name='donor-detail'),
]