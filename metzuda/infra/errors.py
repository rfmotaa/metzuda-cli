"""Custom exception classes for Metzuda infrastructure."""

class QuotaExceededError(Exception):
    """Raised when the user's monthly AI scan quota is exceeded."""
    pass

class RateLimitError(Exception):
    """Raised when API rate limits are exceeded."""
    pass
