from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
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
        
        serializer = DonorListSerializer(filtered_donors, many=True)
        return Response({
            'count': filtered_donors.count(),
            'donors': serializer.data
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