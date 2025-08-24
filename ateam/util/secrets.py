"""Secrets redaction utility for filtering sensitive information from logs and output."""

import os
import re
from typing import List, Pattern, Optional


class SecretsRedactor:
    """Redact sensitive information from text using configurable regex patterns."""
    
    def __init__(self, patterns: Optional[List[str]] = None) -> None:
        """Initialize with custom patterns or load from environment."""
        if patterns is None:
            patterns = self._load_default_patterns()
        
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def _load_default_patterns(self) -> List[str]:
        """Load redaction patterns from environment or use defaults."""
        # Get patterns from environment variable
        env_patterns = os.environ.get("ATEAM_SECRETS_PATTERNS")
        if env_patterns:
            return [p.strip() for p in env_patterns.split(",") if p.strip()]
        
        # Default patterns for common sensitive data
        return [
            # API keys and tokens
            r'(api[_-]?key|token|secret|password|auth)[\s]*[=:]\s*["\']?[a-zA-Z0-9\-_]{16,}["\']?',
            
            # Redis URLs with passwords
            r'redis://[^:]*:[^@]*@[^\s]+',
            
            # SSH private keys
            r'-----BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----[\s\S]*?-----END\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----',
            
            # AWS credentials
            r'(aws_access_key_id|aws_secret_access_key|aws_session_token)[\s]*[=:]\s*["\']?[a-zA-Z0-9\-_]{20,}["\']?',
            
            # Database connection strings
            r'(postgresql|mysql|mongodb)://[^:]*:[^@]*@[^\s]+',
            
            # JWT tokens
            r'eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+',
            
            # Credit card numbers (basic pattern)
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            
            # Social security numbers (US)
            r'\b\d{3}-\d{2}-\d{4}\b',
            
            # Phone numbers
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            
            # Email addresses (optional - can be disabled)
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ]
    
    def redact(self, text: str, replacement: str = "***REDACTED***") -> str:
        """Redact sensitive information from text."""
        if not text:
            return text
        
        redacted = text
        
        for pattern in self.patterns:
            redacted = pattern.sub(replacement, redacted)
        
        return redacted
    
    def redact_dict(self, data: dict, replacement: str = "***REDACTED***") -> dict:
        """Redact sensitive information from dictionary values."""
        if not data:
            return data
        
        redacted = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = self.redact(value, replacement)
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value, replacement)
            elif isinstance(value, list):
                redacted[key] = [
                    self.redact_dict(item, replacement) if isinstance(item, dict)
                    else self.redact(item, replacement) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                redacted[key] = value
        
        return redacted
    
    def add_pattern(self, pattern: str) -> None:
        """Add a new redaction pattern."""
        self.patterns.append(re.compile(pattern, re.IGNORECASE))
    
    def remove_pattern(self, pattern: str) -> None:
        """Remove a redaction pattern."""
        pattern_obj = re.compile(pattern, re.IGNORECASE)
        self.patterns = [p for p in self.patterns if p.pattern != pattern_obj.pattern]


# Global instance for easy access
_redactor: Optional[SecretsRedactor] = None


def get_redactor() -> SecretsRedactor:
    """Get the global secrets redactor instance."""
    global _redactor
    if _redactor is None:
        _redactor = SecretsRedactor()
    return _redactor


def redact(text: str, replacement: str = "***REDACTED***") -> str:
    """Redact sensitive information from text using global redactor."""
    return get_redactor().redact(text, replacement)


def redact_dict(data: dict, replacement: str = "***REDACTED***") -> dict:
    """Redact sensitive information from dictionary using global redactor."""
    return get_redactor().redact_dict(data, replacement)
