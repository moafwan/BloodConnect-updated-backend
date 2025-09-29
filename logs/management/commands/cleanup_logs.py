from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from logs.models import LogEntry

class Command(BaseCommand):
    help = 'Clean up old log entries'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete logs older than this many days (default: 90)'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        deleted_count, _ = LogEntry.objects.filter(timestamp__lt=cutoff_date).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Deleted {deleted_count} log entries older than {days} days")
        )