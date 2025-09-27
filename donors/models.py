from django.db import models
from accounts.models import User

class Donor(models.Model):
    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    )
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES)
    weight = models.DecimalField(max_digits=5, decimal_places=2)  # in kg
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # in cm
    
    # Contact details
    emergency_contact = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    
    # Health information
    has_chronic_disease = models.BooleanField(default=False)
    chronic_disease_details = models.TextField(blank=True)
    recent_medications = models.TextField(blank=True)
    recent_surgeries = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    
    # Donation history
    last_donation_date = models.DateField(null=True, blank=True)
    total_donations = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    
    # Verification status
    is_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.blood_group})"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def can_donate(self):
        if self.age < 18 or self.age > 60:
            return False, "Age must be between 18 and 60 years"
        if self.weight < 45:
            return False, "Weight must be at least 45 kg"
        if self.has_chronic_disease:
            return False, "Cannot donate due to chronic disease"
        return True, "Eligible to donate"