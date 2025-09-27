import logging
from django.db import connection

class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        try:
            # Check if database is ready and LogEntry table exists
            if connection.connection is None:
                return
                
            from .models import LogEntry
            
            # Extract user info safely
            user_id = getattr(record, 'user_id', None)
            ip_address = getattr(record, 'ip_address', None)
            request_path = getattr(record, 'request_path', '')
            
            LogEntry.objects.create(
                level=record.levelname,
                message=self.format(record),
                module=record.module,
                user_id=user_id,
                ip_address=ip_address,
                request_path=request_path
            )
        except Exception as e:
            # Fallback to console logging if database logging fails
            print(f"Database logging failed: {e}")