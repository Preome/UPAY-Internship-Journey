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
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('request_logger')
        self.logger.setLevel(logging.INFO)
        
        # Check if handler already exists to avoid duplicates
        if not self.logger.handlers:
            # Create file handler
            log_file = os.path.join(log_dir, 'requests.log')
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # Add handler to logger
            self.logger.addHandler(file_handler)
            
            # Prevent propagation to root logger
            self.logger.propagate = False
    
    def __call__(self, request):
        # Record start time
        start_time = timezone.now()
        
        # Process the request and get response
        response = self.get_response(request)
        
        # Calculate request processing time
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds() * 1000  # Convert to milliseconds
        
        # Get client IP address
        ip_address = self.get_client_ip(request)
        
        # Get User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        # Get request method and path
        method = request.method
        path = request.get_full_path()
        
        # Get status code from response
        status_code = response.status_code
        
        # Prepare log message
        log_message = (
            f"IP: {ip_address:<15} | "
            f"Method: {method:<6} | "
            f"Path: {path:<30} | "
            f"Status: {status_code} | "
            f"Time: {duration:.2f}ms | "
            f"User-Agent: {user_agent[:50]}"
        )
        
        # Write to log file
        self.logger.info(log_message)
        
        # Also print to console if in debug mode
        if settings.DEBUG:
            print(f"[REQUEST] {log_message}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        
        if x_forwarded_for:
            # Get the first IP in the X-Forwarded-For header
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        return ip