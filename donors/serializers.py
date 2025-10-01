from rest_framework import serializers
from .models import Donor

class DonorRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donor
        fields = '__all__'
        read_only_fields = ('is_verified', 'verification_notes', 'last_donation_date', 'total_donations', 'created_at', 'updated_at')
    
    def validate(self, attrs):
        # Age validation
        from datetime import date
        if 'date_of_birth' in attrs:
            age = date.today().year - attrs['date_of_birth'].year
            if age < 18 or age > 60:
                raise serializers.ValidationError({"date_of_birth": "Age must be between 18 and 60 years"})
        
        # Weight validation
        if 'weight' in attrs and attrs['weight'] < 45:
            raise serializers.ValidationError({"weight": "Weight must be at least 45 kg"})
            
        return attrs

    def create(self, validated_data):
        # Ensure user is properly set
        return Donor.objects.create(**validated_data)
    
class DonorListSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    eligibility_status = serializers.SerializerMethodField()
    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField()
    
    class Meta:
        model = Donor
        fields = ('id', 'full_name', 'blood_group', 'age', 'gender', 
                 'city', 'state', 'country', 'is_available', 'eligibility_status')
    
    def get_eligibility_status(self, obj):
        can_donate, message = obj.can_donate()
        return message

class DonorDetailSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    email = serializers.CharField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    can_donate_now = serializers.SerializerMethodField()
    next_eligible_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Donor
        fields = '__all__'
    
    def get_can_donate_now(self, obj):
        can_donate, _ = obj.can_donate()
        return can_donate
    
    def get_next_eligible_date(self, obj):
        if obj.last_donation_date:
            from dateutil.relativedelta import relativedelta
            return obj.last_donation_date + relativedelta(months=3)
        return None