"""
Hebrew response templates for each conversation state.
Dynamic values are filled via str.format(**data).
"""
from app.tenants.models import ClinicConfig


def greeting(clinic: ClinicConfig) -> str:
    return (
        f"שלום! אני הבוט של {clinic.name} 😊\n\n"
        "במה אוכל לעזור לך היום?\n\n"
        "1️⃣ קביעת תור\n"
        "2️⃣ ביטול תור\n"
        "3️⃣ שינוי / עדכון תור\n"
        "4️⃣ שאלה כללית\n"
        "5️⃣ דיבור עם נציג"
    )


def ask_name() -> str:
    return "מצוין! נשמח לקבוע עבורך תור 😊\nמה שמך המלא?"


def ask_service(clinic: ClinicConfig) -> str:
    lines = [f"{i + 1}️⃣ {s.name_he}" for i, s in enumerate(clinic.services)]
    return "איזה טיפול תרצה?\n\n" + "\n".join(lines)


def ask_date(name: str) -> str:
    return f"תודה {name}! 🗓️\nמתי נוח לך לבוא?\nאנא כתוב תאריך (לדוגמה: יום שני, 23/06, מחר)"


def ask_time(date_text: str, slots: list[str]) -> str:
    if not slots:
        return f"מצטערים, אין שעות פנויות ב{date_text}.\nנסה תאריך אחר?"
    slots_text = "\n".join(f"{i + 1}️⃣ {s}" for i, s in enumerate(slots))
    return f"השעות הפנויות ב{date_text}:\n\n{slots_text}\n\nבחר מספר שעה."


def booking_confirm(name: str, service_name: str, date_text: str, time_text: str) -> str:
    return (
        "✅ סיכום התור שלך:\n\n"
        f"👤 שם: {name}\n"
        f"💆 טיפול: {service_name}\n"
        f"📅 תאריך: {date_text}\n"
        f"🕐 שעה: {time_text}\n\n"
        "לאישור הזמנה שלח *כן* ✅\n"
        "לביטול שלח *לא* ❌"
    )


def booking_done(ref_code: str, date_text: str, time_text: str) -> str:
    return (
        "🎉 תורך נקבע בהצלחה!\n\n"
        f"📋 מספר אסמכתא: *{ref_code}*\n"
        f"📅 {date_text} בשעה {time_text}\n\n"
        "לביטול או שינוי תור בכל עת, שלח *ביטול* או *שינוי*.\n"
        "נתראה! 😊"
    )


def ask_cancel_ref() -> str:
    return (
        "לביטול תור, אנא שלח את *מספר האסמכתא* שקיבלת בעת הזמנה\n"
        "(לדוגמה: WEL-2024-0042)\n\n"
        "לא זוכר את המספר? שלח את *מספר הטלפון* שבו נרשמת."
    )


def cancel_confirm(service_name: str, date_text: str, time_text: str) -> str:
    return (
        "מצאתי את התור שלך:\n\n"
        f"💆 טיפול: {service_name}\n"
        f"📅 תאריך: {date_text}\n"
        f"🕐 שעה: {time_text}\n\n"
        "לאישור ביטול שלח *כן* ✅\n"
        "לביטול הביטול שלח *לא* ❌"
    )


def cancel_done() -> str:
    return (
        "✅ התור בוטל בהצלחה.\n\n"
        "נשמח לראותך שוב בקרוב!\n"
        "לקביעת תור חדש שלח *תור* בכל עת."
    )


def appointment_not_found() -> str:
    return (
        "מצטערים, לא מצאתי תור בשמך.\n\n"
        "האם מספר האסמכתא נכון? נסה שוב או שלח *נציג* לעזרה."
    )


def ask_update_what() -> str:
    return (
        "מה תרצה לעדכן בתור?\n\n"
        "1️⃣ תאריך ושעה\n"
        "2️⃣ סוג הטיפול\n"
        "3️⃣ הכל מחדש"
    )


def update_done(ref_code: str) -> str:
    return (
        f"✅ התור עודכן בהצלחה!\n"
        f"מספר אסמכתא: *{ref_code}*\n\n"
        "נתראה! 😊"
    )


def human_handoff(message: str) -> str:
    return message


def error_message() -> str:
    return "מצטערים, נתקלנו בבעיה טכנית. אנא נסה שוב או שלח *נציג* לעזרה."


def unknown_input() -> str:
    return (
        "לא הבנתי את בקשתך. 🤔\n\n"
        "תוכל לשלח:\n"
        "• *תור* – לקביעת תור\n"
        "• *ביטול* – לביטול תור\n"
        "• *שינוי* – לשינוי תור\n"
        "• *עזרה* – לדיבור עם נציג"
    )
