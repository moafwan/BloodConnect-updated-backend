from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q
from django.utils import timezone  # ADD THIS IMPORT
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
        
        # Check if hospital staff and hospital are active
        hospital_staff = HospitalStaff.objects.get(user=request.user)
        if not hospital_staff.hospital.is_active:
            return Response({'error': 'Hospital account is not active'}, status=status.HTTP_403_FORBIDDEN)
        
        hospital = hospital_staff.hospital
        
        data = request.data.copy()
        data['hospital'] = hospital.id
        
        serializer = BloodRequestSerializer(data=data)
        if serializer.is_valid():
            # Create the blood request with 'pending' status (default)
            blood_request = serializer.save()
            
            logger.info(f"Blood request created: {blood_request.id} by hospital {hospital.name} - Awaiting approval")
            
            return Response({
                'message': 'Blood request submitted for verification. Donors will be notified once approved.',
                'request_id': blood_request.id,
                'status': 'pending_approval'
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
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_stats(request):
    """Get statistics for hospital dashboard"""
    try:
        if request.user.user_type != 'hospital_staff':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get hospital associated with the staff user
        hospital_staff = HospitalStaff.objects.get(user=request.user)
        hospital = hospital_staff.hospital
        
        # Get total requests made by this hospital
        total_requests = BloodRequest.objects.filter(hospital=hospital).count()
        
        # Get requests by status
        pending_requests = BloodRequest.objects.filter(
            hospital=hospital, 
            status='pending'
        ).count()
        
        approved_requests = BloodRequest.objects.filter(
            hospital=hospital, 
            status='approved'
        ).count()
        
        completed_requests = BloodRequest.objects.filter(
            hospital=hospital, 
            status='completed'
        ).count()
        
        rejected_requests = BloodRequest.objects.filter(
            hospital=hospital, 
            status='rejected'
        ).count()
        
        # Get available donors count (filter by location if needed)
        available_donors = Donor.objects.filter(
            is_verified=True, 
            is_available=True
        ).count()
        
        # Calculate success rate (completed / total, excluding pending)
        total_processed = total_requests - pending_requests
        success_rate = 0
        if total_processed > 0:
            success_rate = round((completed_requests / total_processed) * 100)
        
        # Get this month's requests
        this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_requests = BloodRequest.objects.filter(
            hospital=hospital,
            created_at__gte=this_month
        ).count()
        
        return Response({
            'total_requests': total_requests,
            'pending_requests': pending_requests,
            'approved_requests': approved_requests,
            'completed_requests': completed_requests,
            'rejected_requests': rejected_requests,
            'available_donors': available_donors,
            'success_rate': success_rate,
            'this_month_requests': this_month_requests,
        })
        
    except HospitalStaff.DoesNotExist:
        return Response({'error': 'Hospital staff not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Hospital stats error: {str(e)}")
        return Response({'error': 'Failed to fetch hospital statistics'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_stats(request):
    """Get detailed request statistics for quick stats section"""
    try:
        if request.user.user_type != 'hospital_staff':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        hospital_staff = HospitalStaff.objects.get(user=request.user)
        hospital = hospital_staff.hospital
        
        # Get counts by status
        stats = {
            'pending': BloodRequest.objects.filter(hospital=hospital, status='pending').count(),
            'approved': BloodRequest.objects.filter(hospital=hospital, status='approved').count(),
            'completed': BloodRequest.objects.filter(hospital=hospital, status='completed').count(),
            'rejected': BloodRequest.objects.filter(hospital=hospital, status='rejected').count(),
        }
        
        return Response(stats)
        
    except HospitalStaff.DoesNotExist:
        return Response({'error': 'Hospital staff not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Request stats error: {str(e)}")
        return Response({'error': 'Failed to fetch request statistics'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)