from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q
from accounts.models import HospitalStaff
from donors.models import Donor
from requests.models import BloodRequest, DonorNotification
from requests.serializers import BloodRequestSerializer
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_blood_request(request):
    try:
        if request.user.user_type != 'hospital_staff':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # ENHANCED: Check if hospital staff and hospital are active
        hospital_staff = HospitalStaff.objects.get(user=request.user)
        if not hospital_staff.hospital.is_active:
            return Response({'error': 'Hospital account is not active'}, status=status.HTTP_403_FORBIDDEN)
        
        hospital = hospital_staff.hospital
        
        data = request.data.copy()
        data['hospital'] = hospital.id
        
        serializer = BloodRequestSerializer(data=data)
        if serializer.is_valid():
            blood_request = serializer.save()
            
            # Find matching donors
            donors = Donor.objects.filter(
                blood_group=data['blood_group'],
                is_verified=True,
                is_available=True
            )
            
            # Create notifications for donors
            notifications = []
            for donor in donors:
                notification = DonorNotification(
                    blood_request=blood_request,
                    donor=donor,
                    status='pending'
                )
                notifications.append(notification)
            
            DonorNotification.objects.bulk_create(notifications)
            
            logger.info(f"Blood request created: {blood_request.id} by hospital {hospital.name}")
            return Response({
                'message': 'Blood request submitted for verification',
                'request_id': blood_request.id,
                'notifications_sent': len(notifications)
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except HospitalStaff.DoesNotExist:
        return Response({'error': 'Hospital staff not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Blood request creation error: {str(e)}")
        return Response({'error': 'Failed to create blood request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_requests(request):
    try:
        if request.user.user_type != 'hospital_staff':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        hospital_staff = HospitalStaff.objects.get(user=request.user)
        blood_requests = BloodRequest.objects.filter(hospital=hospital_staff.hospital)
        
        serializer = BloodRequestSerializer(blood_requests, many=True)
        return Response({
            'count': blood_requests.count(),
            'requests': serializer.data
        })
    except HospitalStaff.DoesNotExist:
        return Response({'error': 'Hospital staff not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Hospital requests fetch error: {str(e)}")
        return Response({'error': 'Failed to fetch requests'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_profile(request):
    """Get hospital profile for staff members"""
    try:
        if request.user.user_type != 'hospital_staff':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        hospital_staff = HospitalStaff.objects.get(user=request.user)
        hospital = hospital_staff.hospital
        
        return Response({
            'hospital_id': hospital.id,
            'name': hospital.name,
            'email': hospital.email,
            'phone_number': hospital.phone_number,
            'address': hospital.address,
            'city': hospital.city,
            'state': hospital.state,
            'country': hospital.country,
            'license_number': hospital.license_number,
            'is_active': hospital.is_active,
            'staff_designation': hospital_staff.designation,
            'is_primary_contact': hospital_staff.is_primary_contact
        })
    except HospitalStaff.DoesNotExist:
        return Response({'error': 'Hospital staff not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Hospital profile error: {str(e)}")
        return Response({'error': 'Failed to fetch hospital profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
