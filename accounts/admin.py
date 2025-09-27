from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Hospital, HospitalStaff

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_verified', 'is_active')
    list_filter = ('user_type', 'is_verified', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('user_type', 'phone_number', 'is_verified')}),
    )

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'username', 'city', 'state', 'is_active')
    list_filter = ('city', 'state', 'is_active')
    search_fields = ('name', 'username', 'license_number')

@admin.register(HospitalStaff)
class HospitalStaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'hospital', 'designation', 'is_primary_contact')
    list_filter = ('hospital', 'designation')