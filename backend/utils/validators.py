import re
from datetime import datetime

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    return True, "Password is valid"

def parse_date(date_string):
    """Parse date string to datetime"""
    try:
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except:
        try:
            return datetime.strptime(date_string, '%Y-%m-%d')
        except:
            return None