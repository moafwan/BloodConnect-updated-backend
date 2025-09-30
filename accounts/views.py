from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Hospital, HospitalStaff
import logging
from logs.utils import DatabaseLogger
from .serializers import (
    UserRegistrationSerializer, HospitalRegistrationSerializer,
    UserLoginSerializer, UserProfileSerializer
)

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def donor_registration(request):
    try:
        data = request.data.copy()
        
        # Extract user registration data
        user_data = {
            'username': data.get('username'),
            'email': data.get('email'),
            'password': data.get('password'),
            'password2': data.get('password2'),
            'user_type': 'donor',
            'phone_number': data.get('phone_number', '')
        }
        
        # Validate user registration data
        user_serializer = UserRegistrationSerializer(data=user_data)
        if user_serializer.is_valid():
            user = user_serializer.save()
            
            # LAZY IMPORTS to avoid circular dependency
            from donors.models import Donor
            from donors.serializers import DonorRegistrationSerializer
            
            donor_data = {
                'user': user.id,
                'full_name': data.get('full_name', ''),
                'date_of_birth': data.get('date_of_birth'),
                'gender': data.get('gender'),
                'blood_group': data.get('blood_group'),
                'weight': data.get('weight'),
                'height': data.get('height', None),
                'emergency_contact': data.get('emergency_contact'),
                'address': data.get('address'),
                'city': data.get('city'),
                'state': data.get('state'),
                'country': data.get('country'),
                'pincode': data.get('pincode'),
                'has_chronic_disease': data.get('has_chronic_disease', False),
                'chronic_disease_details': data.get('chronic_disease_details', ''),
                'recent_medications': data.get('recent_medications', ''),
                'recent_surgeries': data.get('recent_surgeries', ''),
                'allergies': data.get('allergies', '')
            }
            
            donor_serializer = DonorRegistrationSerializer(data=donor_data)
            if donor_serializer.is_valid():
                donor = donor_serializer.save()
                
                logger.info(f"New donor registered: {user.username}")
                return Response({
                    'message': 'Thank you for registering! We will verify your details and contact you soon.',
                    'user_id': user.id,
                    'donor_id': donor.id
                }, status=status.HTTP_201_CREATED)
            else:
                # If donor creation fails, delete the user
                user.delete()
                return Response({
                    'error': 'Donor profile creation failed',
                    'details': donor_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response({
            'error': 'User registration failed',
            'details': user_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Donor registration error: {str(e)}")
        return Response({
            'error': 'Registration failed due to server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def hospital_registration(request):
    try:
        print("=== HOSPITAL REGISTRATION REQUEST ===")
        print("Request data:", request.data)
        
        serializer = HospitalRegistrationSerializer(data=request.data)
        print("Serializer created")
        
        if serializer.is_valid():
            print("Serializer is valid")
            hospital = serializer.save()
            print(f"Hospital created: {hospital.name}")
            logger.info(f"New hospital registered: {hospital.name}")
            return Response({
                'message': 'Hospital registration submitted for verification',
                'hospital_id': hospital.id
            }, status=status.HTTP_201_CREATED)
        else:
            print("Serializer errors:", serializer.errors)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        print("=== HOSPITAL REGISTRATION EXCEPTION ===")
        print("Error type:", type(e).__name__)
        print("Error message:", str(e))
        import traceback
        print("Traceback:", traceback.format_exc())
        
        logger.error(f"Hospital registration error: {str(e)}")
        return Response({
            'error': 'Registration failed',
            'debug_info': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    try:
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            
            if user:
                if not user.is_verified and user.user_type != 'donor':
                    return Response({
                        'error': 'Account pending verification'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                refresh = RefreshToken.for_user(user)
                logger.info(f"User logged in: {username}")
                
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user_type': user.user_type,
                    'is_verified': user.is_verified
                }, status=status.HTTP_200_OK)
            
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response({'error': 'Login failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    try:
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Profile fetch error: {str(e)}")
        return Response({'error': 'Profile fetch failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)