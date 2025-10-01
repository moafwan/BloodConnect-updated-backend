from django.db import models
from accounts.models import User

class DonorManager(models.Manager):
    def get_eligible_donors(self, blood_group=None, city=None):
        """Get donors who are currently eligible to donate"""
        queryset = self.filter(
            is_verified=True,
            is_available=True
        )
        
        if blood_group:
            queryset = queryset.filter(blood_group=blood_group)
            
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        # Filter eligible donors
        eligible_donors = []
        for donor in queryset:
            can_donate, _ = donor.can_donate()
            if can_donate:
                eligible_donors.append(donor)
        
        return eligible_donors
    
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

    objects = DonorManager()

    
    def update_donation_record(self):
        """Update donor's donation records after successful donation"""
        from datetime import date
        self.last_donation_date = date.today()
        self.total_donations = models.F('total_donations') + 1
        self.save(update_fields=['last_donation_date', 'total_donations'])
    
    def can_donate_based_on_time(self):
        """Check if donor can donate based on time gap (3 months)"""
        if not self.last_donation_date:
            return True, "Eligible to donate"
        
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        next_eligible_date = self.last_donation_date + relativedelta(months=3)
        today = date.today()
        
        if today < next_eligible_date:
            days_remaining = (next_eligible_date - today).days
            return False, f"Must wait {days_remaining} more days before next donation (3-month gap required)"
        
        return True, "Eligible to donate"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def can_donate(self):
        """Enhanced eligibility check including time gap"""
        # Basic eligibility checks
        if self.age < 18 or self.age > 60:
            return False, "Age must be between 18 and 60 years"
        if self.weight < 45:
            return False, "Weight must be at least 45 kg"
        if self.has_chronic_disease:
            return False, "Cannot donate due to chronic disease"
        
        # Time gap check
        can_donate_time, time_message = self.can_donate_based_on_time()
        if not can_donate_time:
            return False, time_message
        
        return True, "Eligible to donate"
    
    def get_gender_display(self):
        """Get human-readable gender"""
        gender_dict = dict(self.GENDER_CHOICES)
        return gender_dict.get(self.gender, self.gender)

    @classmethod
    def get_eligible_donors_for_request(cls, blood_request):
        """Get eligible donors for a specific blood request"""
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        # Base queryset
        donors = cls.objects.filter(
            blood_group=blood_request.blood_group,
            is_verified=True,
            is_available=True
        )
        
        # Filter donors who passed the 3-month gap or never donated
        three_months_ago = date.today() - relativedelta(months=3)
        eligible_donors = []
        
        for donor in donors:
            # Check basic eligibility + time gap
            can_donate, _ = donor.can_donate()
            if can_donate:
                eligible_donors.append(donor)
        
        return eligible_donors