from enum import StrEnum


class ConversationState(StrEnum):
    IDLE = "idle"
    GREETING = "greeting"

    # Booking flow
    BOOKING_NAME = "booking_name"
    BOOKING_SERVICE = "booking_service"
    BOOKING_DATE = "booking_date"
    BOOKING_TIME = "booking_time"
    BOOKING_CONFIRM = "booking_confirm"
    BOOKING_DONE = "booking_done"

    # Cancel flow
    CANCEL_LOOKUP = "cancel_lookup"
    CANCEL_CONFIRM = "cancel_confirm"
    CANCEL_DONE = "cancel_done"

    # Update flow
    UPDATE_LOOKUP = "update_lookup"
    UPDATE_FIELD = "update_field"
    UPDATE_CONFIRM = "update_confirm"
    UPDATE_DONE = "update_done"

    # Other
    FAQ = "faq"
    HUMAN_HANDOFF = "human_handoff"
