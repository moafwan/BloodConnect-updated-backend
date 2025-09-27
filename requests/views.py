from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import BloodRequest, DonorNotification, DonationRecord
from .serializers import BloodRequestSerializer, DonorNotificationSerializer
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
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
        blood_request.status = 'approved'  # ✅ Change from 'pending' to 'approved'
        blood_request.approved_by = request.user
        blood_request.save()
        
        # Send notifications to donors
        notifications = DonorNotification.objects.filter(blood_request=blood_request)
        for notification in notifications:
            send_donor_notification(notification)
        
        logger.info(f"Blood request approved: {request_id} by {request.user.username}")
        return Response({
            'message': 'Request approved and notifications sent to donors',
            'request_id': blood_request.id,
            'new_status': 'approved'
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
            
            # ✅ FIX: Update blood request status to completed
            blood_request = notification.blood_request
            blood_request.status = 'completed'
            blood_request.save()  # ✅ This was missing!
            
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
    try:
        donor = notification.donor
        subject = 'Blood Donation Request'
        
        message = render_to_string('emails/donation_request.txt', {
            'donor': donor,
            'request': notification.blood_request,
        })
        
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [donor.user.email],
            fail_silently=False,
        )
        logger.info(f"Notification sent to donor: {donor.user.email}")
    except Exception as e:
        logger.error(f"Email sending error: {str(e)}")

def notify_other_donors(blood_request, accepted_donor):
    try:
        # Mark other notifications as expired
        other_notifications = DonorNotification.objects.filter(
            blood_request=blood_request
        ).exclude(donor=accepted_donor)
        
        for notification in other_notifications:
            notification.status = 'expired'
            notification.save()
            
            # Send thank you email
            subject = 'Blood Donation Request Update'
            message = render_to_string('emails/request_fulfilled.txt', {
                'donor': notification.donor,
                'accepted_donor': accepted_donor,
            })
            
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [notification.donor.user.email],
                fail_silently=True,
            )
        
        logger.info(f"Other donors notified about fulfilled request: {blood_request.id}")
    except Exception as e:
        logger.error(f"Other donors notification error: {str(e)}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def donor_notifications(request):
    try:
        if request.user.user_type != 'donor':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get donor profile
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