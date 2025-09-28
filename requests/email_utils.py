from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_donation_request_email(notification):
    """
    Send email to donor about a new blood request
    """
    try:
        donor = notification.donor
        blood_request = notification.blood_request
        
        subject = f"🩸 Blood Donation Request - {blood_request.patient_name} ({blood_request.blood_group})"
        
        context = {
            'donor': donor,
            'request': blood_request,
            'portal_url': f"{settings.FRONTEND_URL}/donor/notifications" if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000/donor/notifications'
        }
        
        # HTML content
        html_content = render_to_string('emails/donation_request.html', context)
        text_content = strip_tags(render_to_string('emails/donation_request.txt', context))
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[donor.user.email],
            reply_to=[settings.REPLY_TO_EMAIL] if hasattr(settings, 'REPLY_TO_EMAIL') else None
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        logger.info(f"Donation request email sent to {donor.user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send donation request email: {str(e)}")
        return False

def send_request_fulfilled_email(notification, accepted_donor):
    """
    Send email to other donors when a request is fulfilled
    """
    try:
        donor = notification.donor
        blood_request = notification.blood_request
        
        subject = "✅ Blood Request Fulfilled - Thank You!"
        
        context = {
            'donor': donor,
            'request': blood_request,
            'accepted_donor': accepted_donor
        }
        
        # HTML content
        html_content = render_to_string('emails/request_fulfilled.html', context)
        text_content = strip_tags(render_to_string('emails/request_fulfilled.txt', context))
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[donor.user.email],
            reply_to=[settings.REPLY_TO_EMAIL] if hasattr(settings, 'REPLY_TO_EMAIL') else None
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send(fail_silently=True)
        
        logger.info(f"Request fulfilled email sent to {donor.user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send request fulfilled email: {str(e)}")
        return False

def send_hospital_status_email(blood_request, status, accepted_donor=None):
    """
    Send email to hospital about request status changes
    """
    try:
        hospital = blood_request.hospital
        
        # Choose the right template based on status
        if status == 'completed' and accepted_donor:
            subject = f"✅ Blood Request Fulfilled - Donor Found for {blood_request.patient_name}"
            html_template = 'emails/hospital_status_update.html'
            text_template = 'emails/hospital_status_update.txt'
        elif status == 'approved':
            subject = f"✅ Blood Request Approved - {blood_request.patient_name}"
            html_template = 'emails/hospital_request_approved.html'
            text_template = 'emails/hospital_request_approved.txt'
        else:
            subject = f"Blood Request Update - {blood_request.patient_name}"
            html_template = 'emails/hospital_status_update.html'
            text_template = 'emails/hospital_status_update.txt'
        
        # Count requested donors for the approval email
        from .models import DonorNotification
        requested_donors_count = DonorNotification.objects.filter(blood_request=blood_request).count()
        
        context = {
            'request': blood_request,
            'status': status,
            'hospital': hospital,
            'donor': accepted_donor,
            'requested_donors_count': requested_donors_count
        }
        
        # HTML content
        html_content = render_to_string(html_template, context)
        text_content = render_to_string(text_template, context)
        
        # Get hospital staff emails
        from accounts.models import HospitalStaff
        staff_emails = [staff.user.email for staff in HospitalStaff.objects.filter(hospital=hospital) if staff.user.email]
        
        if staff_emails:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=staff_emails
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=True)
            
            logger.info(f"Status update email sent to hospital staff for {blood_request.patient_name} - Status: {status}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to send hospital status email: {str(e)}")
        return False