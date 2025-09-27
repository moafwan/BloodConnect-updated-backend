import logging
from .models import LogEntry

def log_to_db(level, message, module, user_id=None, ip_address=None, request_path=''):
    """
    Utility function to log to database safely
    """
    try:
        LogEntry.objects.create(
            level=level,
            message=message,
            module=module,
            user_id=user_id,
            ip_address=ip_address,
            request_path=request_path
        )
    except Exception as e:
        # Fallback to regular logging
        logger = logging.getLogger(module)
        getattr(logger, level.lower())(message)

# Custom logger that uses database
class DatabaseLogger:
    def __init__(self, module_name):
        self.module_name = module_name
    
    def info(self, message, user_id=None, ip_address=None, request_path=''):
        log_to_db('INFO', message, self.module_name, user_id, ip_address, request_path)
    
    def warning(self, message, user_id=None, ip_address=None, request_path=''):
        log_to_db('WARNING', message, self.module_name, user_id, ip_address, request_path)
    
    def error(self, message, user_id=None, ip_address=None, request_path=''):
        log_to_db('ERROR', message, self.module_name, user_id, ip_address, request_path)
    
    def debug(self, message, user_id=None, ip_address=None, request_path=''):
        log_to_db('DEBUG', message, self.module_name, user_id, ip_address, request_path)