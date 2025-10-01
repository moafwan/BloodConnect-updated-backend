from django.db import models
from donors.models import Donor
from accounts.models import Hospital

class BloodRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    patient_name = models.CharField(max_length=200)
    patient_age = models.IntegerField()
    patient_gender = models.CharField(max_length=1, choices=Donor.GENDER_CHOICES)
    blood_group = models.CharField(max_length=3, choices=Donor.BLOOD_GROUP_CHOICES)
    units_required = models.IntegerField(default=1)
    
    # Medical details
    hemoglobin_level = models.DecimalField(max_digits=4, decimal_places=2)
    diagnosis = models.TextField()
    operation_id = models.CharField(max_length=100, blank=True)
    urgency_level = models.CharField(max_length=20, choices=(
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ))
    
    # Request details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_donors = models.ManyToManyField(Donor, through='DonorNotification')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='approved_requests')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Request for {self.patient_name} ({self.blood_group})"

class DonorNotification(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    )
    
    blood_request = models.ForeignKey(BloodRequest, on_delete=models.CASCADE)
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notification_sent_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('blood_request', 'donor')

# class DonationRecord(models.Model):
#     blood_request = models.ForeignKey(BloodRequest, on_delete=models.CASCADE)
#     donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
#     donation_date = models.DateTimeField(auto_now_add=True)
#     units_donated = models.IntegerField(default=1)
#     notes = models.TextField(blank=True)
    
#     class Meta:
#         unique_together = ('blood_request', 'donor')

class DonationRecord(models.Model):
    blood_request = models.ForeignKey(BloodRequest, on_delete=models.CASCADE)
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    donation_date = models.DateTimeField(auto_now_add=True)  # This automatically sets the timestamp
    units_donated = models.IntegerField(default=1)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('blood_request', 'donor')
    
    def save(self, *args, **kwargs):
        # Ensure donation_date is set to current time if not provided
        if not self.donation_date:
            from django.utils import timezone
            self.donation_date = timezone.now()
        super().save(*args, **kwargs)