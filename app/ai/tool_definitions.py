INTENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "classify_intent",
            "description": "Classify the user's intent from their Hebrew WhatsApp message",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["book", "cancel", "update", "faq", "human", "unknown"],
                        "description": (
                            "book=קביעת תור, cancel=ביטול תור, update=עדכון/שינוי תור, "
                            "faq=שאלה כללית, human=בקשה לנציג אנושי, unknown=לא ברור"
                        ),
                    },
                    "faq_query": {
                        "type": "string",
                        "description": "If action=faq, the user's question reformulated clearly in Hebrew",
                    },
                },
                "required": ["action"],
            },
        },
    }
]

EXTRACT_FIELDS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "extract_appointment_fields",
            "description": "Extract structured appointment fields from a free-text Hebrew user message",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Full name of the patient if mentioned",
                    },
                    "service": {
                        "type": "string",
                        "description": "Service/treatment requested (use the service ID from the config)",
                    },
                    "date_text": {
                        "type": "string",
                        "description": "Date as written by the user (e.g. 'יום שני', '23/06', 'מחר')",
                    },
                    "time_text": {
                        "type": "string",
                        "description": "Time as written by the user (e.g. '10:00', 'עשר בבוקר')",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "True if the user confirmed (כן/אישור/בסדר), False if they declined (לא/בטל)",
                    },
                },
                "required": [],
            },
        },
    }
]
