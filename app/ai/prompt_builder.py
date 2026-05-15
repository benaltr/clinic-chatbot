from app.tenants.models import ClinicConfig


def build_intent_system_prompt(clinic: ClinicConfig) -> str:
    services_list = ", ".join(f"{s.name_he} ({s.id})" for s in clinic.services)
    return (
        f"אתה מסווג כוונות עבור {clinic.name}.\n"
        f"השירותים הזמינים: {services_list}.\n"
        "קבע את כוונת המשתמש מהודעת הווטסאפ שלו בעברית וקרא לפונקציה המתאימה."
    )


def build_faq_system_prompt(clinic: ClinicConfig) -> str:
    return (
        f"{clinic.ai.personality}\n\n"
        "ענה על שאלת המשתמש על סמך המידע שסופק. "
        "אם אין תשובה מספקת במידע הנתון, אמור זאת בנעימות והצע ליצור קשר ישיר עם הקליניקה. "
        "ענה תמיד בעברית."
    )


def build_extract_system_prompt(services: list[str]) -> str:
    services_str = ", ".join(services)
    return (
        "חלץ שדות מובנים מהודעת הוואטסאפ של המשתמש בעברית.\n"
        f"מזהי השירותים הזמינים: {services_str}.\n"
        "החזר רק שדות שהמשתמש ציין במפורש."
    )
