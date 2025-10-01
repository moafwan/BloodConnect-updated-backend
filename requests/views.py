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
            # Check if donor is still eligible (including time gap)
            can_donate, message = notification.donor.can_donate()
            if not can_donate:
                return Response({
                    'error': 'Donation eligibility changed',
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            notification.status = 'accepted'
            notification.responded_at = timezone.now()
            notification.save()
            
            # Create donation record
            donation_record = DonationRecord.objects.create(
                blood_request=notification.blood_request,
                donor=notification.donor,
                units_donated=notification.blood_request.units_required
            )
            
            # ✅ AUTOMATICALLY UPDATE DONOR'S DONATION RECORDS
            notification.donor.update_donation_record()
            
            # Update blood request status to completed
            blood_request = notification.blood_request
            blood_request.status = 'completed'
            blood_request.save()
            
            # Notify other donors that request is fulfilled
            notify_other_donors(blood_request, notification.donor)
            
            return Response({
                'message': 'Thank you for accepting the donation request! Your donation record has been updated.',
                'request_id': blood_request.id,
                'new_status': 'completed',
                'total_donations': notification.donor.total_donations,
                'last_donation_date': notification.donor.last_donation_date
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
        
        # ✅ TIERED DONOR NOTIFICATION SYSTEM
        from donors.models import Donor
        
        logger.info(f"Starting tiered donor search for blood request {request_id} in {blood_request.hospital.city}, {blood_request.hospital.state}")
        
        # Tier 1: Find eligible donors in the SAME CITY as hospital
        local_donors = []
        for donor in Donor.objects.filter(
            blood_group=blood_request.blood_group,
            is_verified=True,
            is_available=True,
            city__iexact=blood_request.hospital.city
        ):
            can_donate, _ = donor.can_donate()
            if can_donate:
                local_donors.append(donor)
        
        logger.info(f"Tier 1 (Same City): Found {len(local_donors)} donors in {blood_request.hospital.city}")
        
        notifications = []
        email_count = 0
        
        # If we have enough local donors (5+), only notify them
        if len(local_donors) >= 5:
            logger.info(f"✅ Enough local donors found ({len(local_donors)}). Notifying only local donors.")
            for donor in local_donors:
                notification = DonorNotification(
                    blood_request=blood_request,
                    donor=donor,
                    status='pending'
                )
                notifications.append(notification)
                logger.info(f" - Local donor: {donor.full_name} in {donor.city}")
        
        else:
            # Tier 2: Not enough local donors, expand to SAME STATE
            logger.info(f"❌ Not enough local donors ({len(local_donors)}). Expanding search to state level.")
            
            # First, add all local donors
            for donor in local_donors:
                notification = DonorNotification(
                    blood_request=blood_request,
                    donor=donor,
                    status='pending'
                )
                notifications.append(notification)
                logger.info(f" - Local donor: {donor.full_name} in {donor.city}")
            
            # Then find donors in the same state but different city
            state_donors = []
            for donor in Donor.objects.filter(
                blood_group=blood_request.blood_group,
                is_verified=True,
                is_available=True,
                state__iexact=blood_request.hospital.state
            ).exclude(city__iexact=blood_request.hospital.city):
                can_donate, _ = donor.can_donate()
                if can_donate:
                    state_donors.append(donor)
            
            logger.info(f"Tier 2 (Same State): Found {len(state_donors)} donors in {blood_request.hospital.state}")
            
            # Add state-level donors
            for donor in state_donors:
                notification = DonorNotification(
                    blood_request=blood_request,
                    donor=donor,
                    status='pending'
                )
                notifications.append(notification)
                logger.info(f" - State donor: {donor.full_name} in {donor.city}, {donor.state}")
            
            # If still not enough, consider national level (optional)
            if len(notifications) < 3:  # If we have very few donors
                national_donors = []
                for donor in Donor.objects.filter(
                    blood_group=blood_request.blood_group,
                    is_verified=True,
                    is_available=True
                ).exclude(state__iexact=blood_request.hospital.state):
                    can_donate, _ = donor.can_donate()
                    if can_donate:
                        national_donors.append(donor)
                
                logger.info(f"Tier 3 (National): Found {len(national_donors)} donors outside {blood_request.hospital.state}")
                
                # Add a limited number of national donors (max 5 to avoid spam)
                for donor in national_donors[:5]:
                    notification = DonorNotification(
                        blood_request=blood_request,
                        donor=donor,
                        status='pending'
                    )
                    notifications.append(notification)
                    logger.info(f" - National donor: {donor.full_name} in {donor.city}, {donor.state}")
        
        # Create all notifications and send emails
        if notifications:
            DonorNotification.objects.bulk_create(notifications)
            logger.info(f"✅ Created {len(notifications)} total notifications")
            
            # Send email notifications
            for notification in notifications:
                if send_donation_request_email(notification):
                    email_count += 1
            
            # Log the distribution
            local_count = len([n for n in notifications if n.donor.city.lower() == blood_request.hospital.city.lower()])
            state_count = len([n for n in notifications if n.donor.state.lower() == blood_request.hospital.state.lower() and n.donor.city.lower() != blood_request.hospital.city.lower()])
            national_count = len([n for n in notifications if n.donor.state.lower() != blood_request.hospital.state.lower()])
            
            logger.info(f"📊 Notification Distribution: Local={local_count}, State={state_count}, National={national_count}")
        
        # Send approval email to hospital
        send_hospital_status_email(blood_request, 'approved')
        
        return Response({
            'message': 'Request approved and notifications sent using tiered system',
            'request_id': blood_request.id,
            'new_status': 'approved',
            'notifications_sent': len(notifications),
            'emails_sent': email_count,
            'distribution': {
                'local_donors': local_count,
                'state_donors': state_count,
                'national_donors': national_count,
                'total_eligible_donors': len(notifications)
            }
        })
        
    except BloodRequest.DoesNotExist:
        return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Request approval error: {str(e)}")
        return Response({'error': 'Failed to approve request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def donor_notifications(request):
    try:
        if request.user.user_type != 'donor':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        from donors.models import Donor
        donor = Donor.objects.get(user=request.user)
        
        # ✅ ONLY show notifications for APPROVED requests where donor was eligible
        notifications = DonorNotification.objects.filter(
            donor=donor, 
            status='pending',
            blood_request__status='approved'
        ).select_related('blood_request', 'blood_request__hospital')
        
        # Double-check current eligibility (in case it changed after notification was sent)
        current_eligible_notifications = []
        for notification in notifications:
            can_donate, _ = donor.can_donate()
            if can_donate:
                current_eligible_notifications.append(notification)
        
        serializer = DonorNotificationSerializer(current_eligible_notifications, many=True)
        return Response({
            'count': len(current_eligible_notifications),
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