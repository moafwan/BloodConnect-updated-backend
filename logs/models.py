from django.db import models
from django.contrib.auth import get_user_model

class LogEntry(models.Model):
    LEVEL_CHOICES = (
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('DEBUG', 'Debug'),
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    message = models.TextField()
    module = models.CharField(max_length=100)
    user_id = models.IntegerField(null=True, blank=True)  # Store user ID instead of ForeignKey initially
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Log entries'

    def __str__(self):
        return f"{self.timestamp} - {self.level} - {self.message[:100]}"
    
    @property
    def user(self):
        User = get_user_model()
        try:
            return User.objects.get(id=self.user_id)
        except User.DoesNotExist:
            return None