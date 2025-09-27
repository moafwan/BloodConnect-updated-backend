from rest_framework import serializers
from .models import BloodRequest, DonorNotification, DonationRecord
from accounts.serializers import HospitalRegistrationSerializer

class BloodRequestSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)
    hospital_city = serializers.CharField(source='hospital.city', read_only=True)
    
    class Meta:
        model = BloodRequest
        fields = '__all__'
        read_only_fields = ('status', 'approved_by', 'created_at', 'updated_at')

class DonorNotificationSerializer(serializers.ModelSerializer):
    donor_name = serializers.CharField(source='donor.full_name', read_only=True)
    donor_blood_group = serializers.CharField(source='donor.blood_group', read_only=True)
    donor_contact = serializers.CharField(source='donor.user.phone_number', read_only=True)
    request_details = BloodRequestSerializer(source='blood_request', read_only=True)
    
    class Meta:
        model = DonorNotification
        fields = '__all__'

class DonationRecordSerializer(serializers.ModelSerializer):
    donor_name = serializers.CharField(source='donor.full_name', read_only=True)
    patient_name = serializers.CharField(source='blood_request.patient_name', read_only=True)
    hospital_name = serializers.CharField(source='blood_request.hospital.name', read_only=True)
    
    class Meta:
        model = DonationRecord
        fields = '__all__'