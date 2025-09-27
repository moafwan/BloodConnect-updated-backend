from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Hospital, HospitalStaff

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'user_type', 'phone_number')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class HospitalRegistrationSerializer(serializers.ModelSerializer):
    user = UserRegistrationSerializer(write_only=True)
    
    class Meta:
        model = Hospital
        fields = ('name', 'username', 'email', 'phone_number', 'address', 
                 'city', 'state', 'country', 'license_number', 'user')

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['user_type'] = 'hospital_staff'  # Add user_type here
        
        user_serializer = UserRegistrationSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        hospital = Hospital.objects.create(**validated_data)
        HospitalStaff.objects.create(user=user, hospital=hospital, designation='Staff')
        
        return hospital

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'user_type', 'phone_number', 
                 'first_name', 'last_name', 'is_verified')