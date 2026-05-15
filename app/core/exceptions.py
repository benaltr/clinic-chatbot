class ClinicNotFoundError(Exception):
    """Raised when an incoming WhatsApp number has no registered clinic."""


class InvalidWebhookSignatureError(Exception):
    """Raised when a Meta webhook payload fails signature verification."""


class AppointmentNotFoundError(Exception):
    """Raised when a patient tries to cancel/update an appointment that doesn't exist."""


class SlotNotAvailableError(Exception):
    """Raised when the requested appointment slot is already taken."""


class CalendarProviderError(Exception):
    """Raised for unexpected errors from any CalendarProvider implementation."""
