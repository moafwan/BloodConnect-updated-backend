from django.urls import path
from . import views

urlpatterns = [
    path('register/donor/', views.donor_registration, name='donor-registration'),
    path('register/hospital/', views.hospital_registration, name='hospital-registration'),
    path('login/', views.user_login, name='user-login'),
    path('profile/', views.user_profile, name='user-profile'),
]