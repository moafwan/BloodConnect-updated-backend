from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Donor
from .serializers import DonorListSerializer, DonorDetailSerializer
from .filters import DonorFilter
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def donor_list(request):
    try:
        # Blood bank managers and hospital staff can view all donors
        if request.user.user_type not in ['blood_bank_manager', 'hospital_staff']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        donors = Donor.objects.filter(is_verified=True, is_available=True)
        
        # Apply filters
        donor_filter = DonorFilter(request.GET, queryset=donors)
        filtered_donors = donor_filter.qs
        
        # Enhance donor data with eligibility info
        enhanced_donors = []
        for donor in filtered_donors:
            can_donate, message = donor.can_donate()
            donor_data = DonorListSerializer(donor).data
            donor_data['can_donate_now'] = can_donate
            donor_data['eligibility_message'] = message
            donor_data['last_donation_date'] = donor.last_donation_date
            donor_data['total_donations'] = donor.total_donations
            enhanced_donors.append(donor_data)
        
        return Response({
            'count': filtered_donors.count(),
            'donors': enhanced_donors
        })
    except Exception as e:
        logger.error(f"Donor list error: {str(e)}")
        return Response({'error': 'Failed to fetch donors'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def donor_detail(request, donor_id):
    try:
        if request.user.user_type not in ['blood_bank_manager', 'hospital_staff']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        donor = Donor.objects.get(id=donor_id, is_verified=True)
        serializer = DonorDetailSerializer(donor)
        return Response(serializer.data)
    except Donor.DoesNotExist:
        return Response({'error': 'Donor not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Donor detail error: {str(e)}")
        return Response({'error': 'Failed to fetch donor details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def donor_profile(request):
    """Allow donors to view and update their own profile"""
    try:
        donor = Donor.objects.get(user=request.user)
        
        if request.method == 'GET':
            serializer = DonorDetailSerializer(donor)
            return Response(serializer.data)
            
        elif request.method == 'PUT':
            # Allow updating specific fields
            allowed_fields = ['is_available', 'phone_number', 'address', 'city', 'state', 'emergency_contact']
            update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
            
            serializer = DonorDetailSerializer(donor, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except Donor.DoesNotExist:
        return Response({'error': 'Donor profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Donor profile error: {str(e)}")
        return Response({'error': 'Failed to fetch donor profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def donation_history(request):
    """Get donation history for authenticated donor"""
    try:
        # Check if user is a donor
        if request.user.user_type != 'donor':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get donor profile
        donor = Donor.objects.get(user=request.user)
        
        # Get donation records for this donor
        from requests.models import DonationRecord
        from requests.serializers import DonationRecordSerializer
        
        donations = DonationRecord.objects.filter(donor=donor).select_related(
            'blood_request', 
            'blood_request__hospital'
        ).order_by('-donation_date')
        
        serializer = DonationRecordSerializer(donations, many=True)
        
        return Response({
            'count': donations.count(),
            'donations': serializer.data
        })
        
    except Donor.DoesNotExist:
        return Response({'error': 'Donor profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Donation history error: {str(e)}")
        return Response({'error': 'Failed to fetch donation history'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
