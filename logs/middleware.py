import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class LoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Add basic request info to logger context
        request.info = {
            'user_id': request.user.id if request.user.is_authenticated else None,
            'ip_address': self.get_client_ip(request),
            'request_path': request.path,
        }
        return None

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def process_response(self, request, response):
        # Log the request after it's processed
        if hasattr(request, 'info'):
            user_info = f"user_id:{request.info['user_id']}" if request.info['user_id'] else "anonymous"
            logger.info(
                f"{request.method} {request.path} - {response.status_code} - {user_info}",
                extra={
                    'user_id': request.info['user_id'],
                    'ip_address': request.info['ip_address'],
                    'request_path': request.info['request_path'],
                }
            )
        return response