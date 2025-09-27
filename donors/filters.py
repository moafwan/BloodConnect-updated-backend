import django_filters
from .models import Donor

class DonorFilter(django_filters.FilterSet):
    blood_group = django_filters.ChoiceFilter(choices=Donor.BLOOD_GROUP_CHOICES)
    city = django_filters.CharFilter(lookup_expr='icontains')
    state = django_filters.CharFilter(lookup_expr='icontains')
    country = django_filters.CharFilter(lookup_expr='icontains')
    gender = django_filters.ChoiceFilter(choices=Donor.GENDER_CHOICES)
    
    min_age = django_filters.NumberFilter(method='filter_min_age')
    max_age = django_filters.NumberFilter(method='filter_max_age')
    
    class Meta:
        model = Donor
        fields = ['blood_group', 'city', 'state', 'country', 'gender']
    
    def filter_min_age(self, queryset, name, value):
        from datetime import date
        from dateutil.relativedelta import relativedelta
        max_birth_date = date.today() - relativedelta(years=value)
        return queryset.filter(date_of_birth__lte=max_birth_date)
    
    def filter_max_age(self, queryset, name, value):
        from datetime import date
        from dateutil.relativedelta import relativedelta
        min_birth_date = date.today() - relativedelta(years=value + 1)
        return queryset.filter(date_of_birth__gt=min_birth_date)