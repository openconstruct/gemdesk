"""
Input validation and sanitization for GemDesk
Ensures security and prevents abuse
"""

import os
import re
from urllib.parse import urlparse
from pathlib import Path


# Validation constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB per file
MAX_URL_LENGTH = 2048
MAX_MESSAGE_LENGTH = 50000  # Characters
ALLOWED_URL_SCHEMES = {'http', 'https'}
# Only block truly executable/script files that could harm the system
# Code files (.js, .py, etc.) are allowed since this is a code analysis tool
DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.cmd', '.com', '.scr', '.vbs', '.msi', '.dll'}


class ValidationError(Exception):
    """Custom exception for validation failures"""
    pass


def validate_file_size(file_path):
    """
    Validate file size is within limits
    
    Args:
        file_path: Path to file
        
    Returns:
        int: File size in bytes
        
    Raises:
        ValidationError: If file too large or inaccessible
    """
    try:
        size = os.path.getsize(file_path)
        if size > MAX_FILE_SIZE:
            raise ValidationError(f"File exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit")
        if size == 0:
            raise ValidationError("File is empty")
        return size
    except OSError as e:
        raise ValidationError(f"Cannot access file: {e}")


def validate_file_extension(filename):
    """
    Check for dangerous file extensions
    
    Args:
        filename: Name of file
        
    Raises:
        ValidationError: If extension is dangerous
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext in DANGEROUS_EXTENSIONS:
        raise ValidationError(f"File type {ext} not allowed for security reasons")


def validate_url(url):
    """
    Validate URL is safe and well-formed
    
    Args:
        url: URL string to validate
        
    Returns:
        str: Sanitized URL
        
    Raises:
        ValidationError: If URL is invalid or dangerous
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string")
    
    url = url.strip()
    
    if len(url) > MAX_URL_LENGTH:
        raise ValidationError(f"URL exceeds {MAX_URL_LENGTH} character limit")
    
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            raise ValidationError(f"URL scheme must be http or https, got: {parsed.scheme}")
        
        # Check for localhost/private IPs (SSRF prevention)
        if parsed.hostname:
            hostname = parsed.hostname.lower()
            if any(hostname.startswith(private) for private in 
                   ['localhost', '127.', '10.', '172.16.', '192.168.', '169.254.']):
                raise ValidationError("Cannot access local or private IP addresses")
        
        # Reconstruct clean URL
        return url
        
    except ValueError as e:
        raise ValidationError(f"Malformed URL: {e}")


def validate_message(message):
    """
    Validate user message input
    
    Args:
        message: User message string
        
    Returns:
        str: Sanitized message
        
    Raises:
        ValidationError: If message is invalid
    """
    if not message or not isinstance(message, str):
        raise ValidationError("Message must be a non-empty string")
    
    message = message.strip()
    
    if not message:
        raise ValidationError("Message cannot be empty")
    
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Message exceeds {MAX_MESSAGE_LENGTH} character limit")
    
    # Remove null bytes (can cause issues)
    message = message.replace('\x00', '')
    
    return message


def validate_api_key(api_key):
    """
    Validate Gemini API key format
    
    Args:
        api_key: API key string
        
    Returns:
        bool: True if valid format
        
    Raises:
        ValidationError: If API key format is invalid
    """
    if not api_key or not isinstance(api_key, str):
        raise ValidationError("API key must be a non-empty string")
    
    api_key = api_key.strip()
    
    # Gemini API keys are typically 39 characters starting with "AIza"
    if not api_key.startswith('AIza'):
        raise ValidationError("API key format appears invalid")
    
    if len(api_key) < 30:
        raise ValidationError("API key too short")
    
    # Should only contain alphanumeric and some special chars
    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        raise ValidationError("API key contains invalid characters")
    
    return True


def sanitize_filename(filename):
    """
    Sanitize filename to prevent path traversal
    
    Args:
        filename: Original filename
        
    Returns:
        str: Safe filename
    """
    # Remove path separators
    filename = os.path.basename(filename)
    
    # Remove any remaining path components
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename


def validate_thinking_level(level):
    """
    Validate thinking level parameter
    
    Args:
        level: Thinking level string
        
    Returns:
        str: Validated level
        
    Raises:
        ValidationError: If level is invalid
    """
    valid_levels = {'minimal', 'low', 'medium', 'high'}
    
    if not isinstance(level, str):
        raise ValidationError("Thinking level must be a string")
    
    level = level.lower().strip()
    
    if level not in valid_levels:
        raise ValidationError(f"Thinking level must be one of: {', '.join(valid_levels)}")
    
    return level


def validate_chart_type(chart_type):
    """
    Validate chart type parameter
    
    Args:
        chart_type: Chart type string
        
    Returns:
        str: Validated chart type
        
    Raises:
        ValidationError: If chart type is invalid
    """
    valid_types = {'line', 'bar', 'pie', 'scatter'}
    
    if not isinstance(chart_type, str):
        raise ValidationError("Chart type must be a string")
    
    chart_type = chart_type.lower().strip()
    
    if chart_type not in valid_types:
        raise ValidationError(f"Chart type must be one of: {', '.join(valid_types)}")
    
    return chart_type


def check_rate_limit(last_request_time, min_interval=1.0):
    """
    Simple rate limiting check
    
    Args:
        last_request_time: Timestamp of last request
        min_interval: Minimum seconds between requests
        
    Returns:
        bool: True if request allowed
        
    Raises:
        ValidationError: If rate limit exceeded
    """
    import time
    current_time = time.time()
    
    if last_request_time and (current_time - last_request_time) < min_interval:
        raise ValidationError("Rate limit exceeded. Please wait before sending another request.")
    
    return True
