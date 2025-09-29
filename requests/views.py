from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from .models import BloodRequest, DonorNotification, DonationRecord
from .serializers import BloodRequestSerializer, DonorNotificationSerializer
from .email_utils import send_donation_request_email, send_request_fulfilled_email, send_hospital_status_email
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_requests(request):
    try:
        if request.user.user_type != 'blood_bank_manager':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        pending_requests = BloodRequest.objects.filter(status='pending')
        serializer = BloodRequestSerializer(pending_requests, many=True)
        return Response({
            'count': pending_requests.count(),
            'requests': serializer.data
        })
    except Exception as e:
        logger.error(f"Pending requests fetch error: {str(e)}")
        return Response({'error': 'Failed to fetch pending requests'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_request(request, request_id):
    try:
        if request.user.user_type != 'blood_bank_manager':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        blood_request = BloodRequest.objects.get(id=request_id)
        blood_request.status = 'approved'
        blood_request.approved_by = request.user
        blood_request.save()
        
        # Send notifications to donors
        notifications = DonorNotification.objects.filter(blood_request=blood_request)
        email_count = 0
        
        for notification in notifications:
            if send_donation_request_email(notification):
                email_count += 1
        
        # ✅ FIXED: Send APPROVAL email, not COMPLETED email
        send_hospital_status_email(blood_request, 'approved')  # No donor parameter
        
        logger.info(f"Blood request approved: {request_id} by {request.user.username}")
        return Response({
            'message': 'Request approved and notifications sent to donors',
            'request_id': blood_request.id,
            'new_status': 'approved',
            'emails_sent': email_count
        })
    except BloodRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Request approval error: {str(e)}")
        return Response({'error': 'Failed to approve request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_request(request, request_id):
    try:
        if request.user.user_type != 'blood_bank_manager':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        blood_request = BloodRequest.objects.get(id=request_id)
        blood_request.status = 'rejected'
        blood_request.approved_by = request.user
        blood_request.save()
        
        # Notify hospital about rejection
        send_hospital_status_email(blood_request, 'rejected')
        
        logger.info(f"Blood request rejected: {request_id} by {request.user.username}")
        return Response({'message': 'Request rejected'})
    except BloodRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Request rejection error: {str(e)}")
        return Response({'error': 'Failed to reject request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def donor_response(request, notification_id):
    try:
        notification = DonorNotification.objects.get(id=notification_id)
        
        if notification.donor.user != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        response = request.data.get('response')  # 'accept' or 'decline'
        
        if response == 'accept':
            notification.status = 'accepted'
            notification.responded_at = timezone.now()
            notification.save()
            
            # Create donation record
            DonationRecord.objects.create(
                blood_request=notification.blood_request,
                donor=notification.donor
            )
            
            # Update blood request status to completed
            blood_request = notification.blood_request
            blood_request.status = 'completed'
            blood_request.save()
            
            # Notify other donors that request is fulfilled
            notify_other_donors(blood_request, notification.donor)
            
            return Response({
                'message': 'Thank you for accepting the donation request!',
                'request_id': blood_request.id,
                'new_status': 'completed'
            })
        
        elif response == 'decline':
            notification.status = 'declined'
            notification.responded_at = timezone.now()
            notification.save()
            return Response({'message': 'Thank you for your response.'})
        
        else:
            return Response({'error': 'Invalid response'}, status=status.HTTP_400_BAD_REQUEST)
            
    except DonorNotification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Donor response error: {str(e)}")
        return Response({'error': 'Failed to process response'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def send_donor_notification(notification):
    """
    Wrapper function for backward compatibility
    """
    return send_donation_request_email(notification)

def notify_other_donors(blood_request, accepted_donor):
    """
    Notify other donors that the request has been fulfilled
    """
    try:
        other_notifications = DonorNotification.objects.filter(
            blood_request=blood_request
        ).exclude(donor=accepted_donor)
        
        for notification in other_notifications:
            notification.status = 'expired'
            notification.save()
            
            # Send thank you email using the new email utility
            send_request_fulfilled_email(notification, accepted_donor)
        
        logger.info(f"Other donors notified about fulfilled request: {blood_request.id}")
        
        # ✅ UPDATED: Notify hospital about completion WITH donor details
        send_hospital_status_email(blood_request, 'completed', accepted_donor)
        
    except Exception as e:
        logger.error(f"Other donors notification error: {str(e)}")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def donor_notifications(request):
    try:
        if request.user.user_type != 'donor':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # LAZY IMPORT to avoid circular dependency
        from donors.models import Donor
        donor = Donor.objects.get(user=request.user)
        
        notifications = DonorNotification.objects.filter(
            donor=donor, 
            status='pending'
        ).select_related('blood_request', 'blood_request__hospital')
        
        serializer = DonorNotificationSerializer(notifications, many=True)
        return Response({
            'count': notifications.count(),
            'notifications': serializer.data
        })
    except Donor.DoesNotExist:
        return Response({'error': 'Donor profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Donor notifications error: {str(e)}")
        return Response({'error': 'Failed to fetch notifications'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_email(request):
    """
    Test endpoint to send a test email
    """
    try:
        from donors.models import Donor
        from .models import BloodRequest
        
        # Get the first available donor and request for testing
        donor = Donor.objects.first()
        blood_request = BloodRequest.objects.first()
        
        if not donor or not blood_request:
            return Response({'error': 'No donors or requests available for testing'})
        
        # Create a test notification
        notification = DonorNotification(
            donor=donor,
            blood_request=blood_request,
            status='pending'
        )
        
        # Send test email
        success = send_donation_request_email(notification)
        
        return Response({
            'message': 'Test email sent' if success else 'Failed to send test email',
            'to': donor.user.email,
            'donor': donor.full_name,
            'request': blood_request.patient_name
        })
        
    except Exception as e:
        logger.error(f"Test email error: {str(e)}")
        return Response({'error': 'Test failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)