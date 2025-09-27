from django.contrib import admin
from .models import Donor

@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'blood_group', 'is_verified', 'is_available', 'city')
    list_filter = ('blood_group', 'is_verified', 'is_available', 'city')
    search_fields = ('full_name', 'user__username')
    list_editable = ('is_verified', 'is_available')

# admin.site.register(Donor, DonorAdmin)