RECEPTIONIST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "מחזיר את השעות הפנויות לתאריך מסוים",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "התאריך המבוקש, לדוגמה: מחר, 25/06, יום שלישי",
                    },
                    "service_id": {
                        "type": "string",
                        "description": "מזהה השירות (אופציונלי)",
                    },
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_patient_appointment",
            "description": "מחפש את התור הפעיל של הלקוח לפי מספר הטלפון שלו",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "קובע תור חדש לאחר קבלת אישור מהלקוח",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string"},
                    "service_id": {"type": "string", "description": "מזהה השירות מרשימת השירותים"},
                    "date": {"type": "string"},
                    "time": {"type": "string", "description": "שעה בפורמט HH:MM"},
                },
                "required": ["patient_name", "service_id", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "מבטל תור לאחר קבלת אישור מהלקוח",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                },
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_appointment",
            "description": "מבטל את התור הישן וקובע חדש בתאריך/שעה אחרת, לאחר אישור",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string", "description": "מזהה התור הישן"},
                    "patient_name": {"type": "string"},
                    "service_id": {"type": "string"},
                    "new_date": {"type": "string"},
                    "new_time": {"type": "string", "description": "שעה בפורמט HH:MM"},
                },
                "required": ["appointment_id", "new_date", "new_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "מעביר את השיחה לנציג אנושי",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                },
                "required": [],
            },
        },
    },
]

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
