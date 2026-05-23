import logging
import os
import json
from django.utils import timezone
from django.conf import settings

class RequestLoggerMiddleware:
    """
    Middleware to log request time, IP address, and user agent to a file.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.setup_logger()
        
    def setup_logger(self):
        """Setup logger configuration"""
        
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        
        self.logger = logging.getLogger('request_logger')
        self.logger.setLevel(logging.INFO)
        
        
        if not self.logger.handlers:
            
            log_file = os.path.join(log_dir, 'requests.log')
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            
            
            formatter = logging.Formatter(
                '%(asctime)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            
            self.logger.addHandler(file_handler)
            
            
            self.logger.propagate = False
    
    def __call__(self, request):
        
        start_time = timezone.now()
        
        
        response = self.get_response(request)
        
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds() * 1000  # Convert to milliseconds
        
        
        ip_address = self.get_client_ip(request)
        
        
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        
        method = request.method
        path = request.get_full_path()
        
        
        status_code = response.status_code
        
        
        log_message = (
            f"IP: {ip_address:<15} | "
            f"Method: {method:<6} | "
            f"Path: {path:<30} | "
            f"Status: {status_code} | "
            f"Time: {duration:.2f}ms | "
            f"User-Agent: {user_agent[:50]}"
        )
        
        
        self.logger.info(log_message)
        
        
        if settings.DEBUG:
            print(f"[REQUEST] {log_message}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        
        if x_forwarded_for:
            
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        return ip