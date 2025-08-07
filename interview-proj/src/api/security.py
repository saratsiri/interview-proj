"""Security utilities and middleware for the API"""
import re
import time
import hashlib
import secrets
from typing import Optional, Dict, List
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import html

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, requests_per_minute: int = 10, requests_per_hour: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests = defaultdict(deque)  # IP -> deque of timestamps
        self.hour_requests = defaultdict(deque)
    
    def is_allowed(self, client_ip: str) -> tuple[bool, Optional[str]]:
        """Check if request is allowed for given IP"""
        now = datetime.now()
        
        # Clean old entries
        self._clean_old_requests(client_ip, now)
        
        # Check minute limit
        if len(self.minute_requests[client_ip]) >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
        
        # Check hour limit
        if len(self.hour_requests[client_ip]) >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
        
        # Add current request
        self.minute_requests[client_ip].append(now)
        self.hour_requests[client_ip].append(now)
        
        return True, None
    
    def _clean_old_requests(self, client_ip: str, now: datetime):
        """Remove old requests from tracking"""
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        # Clean minute requests
        while (self.minute_requests[client_ip] and 
               self.minute_requests[client_ip][0] < minute_ago):
            self.minute_requests[client_ip].popleft()
        
        # Clean hour requests  
        while (self.hour_requests[client_ip] and
               self.hour_requests[client_ip][0] < hour_ago):
            self.hour_requests[client_ip].popleft()
    
    def get_status(self, client_ip: str) -> Dict:
        """Get rate limit status for IP"""
        now = datetime.now()
        self._clean_old_requests(client_ip, now)
        
        return {
            "requests_this_minute": len(self.minute_requests[client_ip]),
            "requests_this_hour": len(self.hour_requests[client_ip]),
            "minute_limit": self.requests_per_minute,
            "hour_limit": self.requests_per_hour,
            "minute_remaining": max(0, self.requests_per_minute - len(self.minute_requests[client_ip])),
            "hour_remaining": max(0, self.requests_per_hour - len(self.hour_requests[client_ip]))
        }


class InputSanitizer:
    """Sanitize and validate user inputs"""
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',               # JavaScript protocol
        r'on\w+\s*=',                # Event handlers
        r'<iframe[^>]*>',            # Iframes
        r'<object[^>]*>',            # Objects
        r'<embed[^>]*>',             # Embeds
        r'data:text/html',           # Data URLs
        r'eval\s*\(',                # Eval calls
        r'expression\s*\(',          # CSS expressions
        r'import\s+',                # Import statements
        r'require\s*\(',             # Require calls
    ]
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r'(\bUNION\b|\bSELECT\b|\bINSERT\b|\bDELETE\b|\bUPDATE\b|\bDROP\b)',
        r'(\bOR\b|\bAND\b)\s+(\d+\s*=\s*\d+|\w+\s*=\s*\w+)',
        r'[\'";].*(--)|(\/\*)',
        r'xp_\w+',
        r'sp_\w+',
    ]
    
    @classmethod
    def sanitize_string(cls, text: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not text:
            return ""
        
        # Truncate if too long
        text = text[:max_length]
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # HTML encode dangerous characters
        text = html.escape(text)
        
        # Remove dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential SQL injection attempt blocked: {text[:100]}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected"
                )
        
        return text.strip()
    
    @classmethod
    def sanitize_keywords(cls, keywords: List[str], max_keywords: int = 10, max_length: int = 50) -> List[str]:
        """Sanitize keyword list"""
        if not keywords:
            return []
        
        # Limit number of keywords
        keywords = keywords[:max_keywords]
        
        # Sanitize each keyword
        sanitized = []
        for keyword in keywords:
            if isinstance(keyword, str):
                sanitized_keyword = cls.sanitize_string(keyword, max_length)
                if sanitized_keyword and len(sanitized_keyword.strip()) > 0:
                    # Only allow alphanumeric, spaces, hyphens, underscores
                    if re.match(r'^[a-zA-Z0-9\s\-_]+$', sanitized_keyword):
                        sanitized.append(sanitized_keyword.lower())
        
        return sanitized
    
    @classmethod
    def validate_category(cls, category: str, allowed_categories: List[str]) -> str:
        """Validate category against allowed values"""
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category is required"
            )
        
        sanitized_category = cls.sanitize_string(category, 100)
        
        if sanitized_category not in allowed_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Allowed: {', '.join(allowed_categories)}"
            )
        
        return sanitized_category


class SecurityHeaders:
    """Security headers middleware"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers to add to responses"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), accelerometer=(), "
                "gyroscope=(), interest-cohort=()"
            )
        }


class APIKeyAuth(HTTPBearer):
    """Simple API key authentication"""
    
    def __init__(self, api_keys: Optional[List[str]] = None):
        super().__init__()
        self.api_keys = set(api_keys) if api_keys else set()
        self.enabled = len(self.api_keys) > 0
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        if not self.enabled:
            return None
            
        credentials = await super().__call__(request)
        
        if not credentials or credentials.credentials not in self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return credentials


class RequestValidator:
    """Validate request structure and content"""
    
    MAX_REQUEST_SIZE = 10 * 1024  # 10KB
    MAX_TOPIC_LENGTH = 200
    MAX_KEYWORD_LENGTH = 50
    MAX_KEYWORDS = 10
    MAX_AUDIENCE_LENGTH = 100
    MAX_TONE_LENGTH = 50
    
    @classmethod
    def validate_request_size(cls, request_body: bytes):
        """Validate request size"""
        if len(request_body) > cls.MAX_REQUEST_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request too large. Maximum size: {cls.MAX_REQUEST_SIZE} bytes"
            )
    
    @classmethod
    def validate_content_type(cls, content_type: str):
        """Validate content type"""
        if not content_type or not content_type.startswith('application/json'):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Content-Type must be application/json"
            )
    
    @classmethod
    def validate_json_structure(cls, data: dict):
        """Validate JSON structure"""
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body must be a JSON object"
            )
        
        # Check for excessive nesting
        def check_depth(obj, max_depth=5, current_depth=0):
            if current_depth > max_depth:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="JSON structure too deeply nested"
                )
            
            if isinstance(obj, dict):
                for value in obj.values():
                    check_depth(value, max_depth, current_depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, max_depth, current_depth + 1)
        
        check_depth(data)


class AuditLogger:
    """Audit logging for security events"""
    
    def __init__(self):
        self.logger = logging.getLogger("security_audit")
        
        # Create handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_request(self, request: Request, client_ip: str, user_agent: str):
        """Log incoming request"""
        self.logger.info(
            f"REQUEST - IP: {client_ip}, "
            f"Path: {request.url.path}, "
            f"Method: {request.method}, "
            f"User-Agent: {user_agent[:100]}"
        )
    
    def log_rate_limit_exceeded(self, client_ip: str, limit_type: str):
        """Log rate limit exceeded"""
        self.logger.warning(
            f"RATE_LIMIT_EXCEEDED - IP: {client_ip}, "
            f"Limit Type: {limit_type}"
        )
    
    def log_security_violation(self, client_ip: str, violation_type: str, details: str):
        """Log security violation"""
        self.logger.error(
            f"SECURITY_VIOLATION - IP: {client_ip}, "
            f"Type: {violation_type}, "
            f"Details: {details[:200]}"
        )
    
    def log_auth_failure(self, client_ip: str, reason: str):
        """Log authentication failure"""
        self.logger.warning(
            f"AUTH_FAILURE - IP: {client_ip}, "
            f"Reason: {reason}"
        )


# Global instances
rate_limiter = RateLimiter(requests_per_minute=20, requests_per_hour=200)
input_sanitizer = InputSanitizer()
security_headers = SecurityHeaders()
request_validator = RequestValidator()
audit_logger = AuditLogger()


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for forwarded headers (when behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in case of multiple proxies
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    if hasattr(request, 'client') and request.client:
        return request.client.host
    
    return "unknown"


def generate_api_key(length: int = 32) -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(length)


def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


# Export main security functions
__all__ = [
    'RateLimiter', 
    'InputSanitizer', 
    'SecurityHeaders', 
    'APIKeyAuth',
    'RequestValidator',
    'AuditLogger',
    'rate_limiter',
    'input_sanitizer', 
    'security_headers',
    'request_validator',
    'audit_logger',
    'get_client_ip',
    'generate_api_key',
    'hash_api_key'
]