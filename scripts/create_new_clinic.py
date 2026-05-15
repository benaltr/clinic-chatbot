"""
Scaffold a new clinic config folder from a template.
Usage: python -m scripts.create_new_clinic <clinic_id> <clinic_name_he> <whatsapp_number>
Example: python -m scripts.create_new_clinic my_spa "ספא שלי" +972501234570
"""
import sys
from pathlib import Path

TEMPLATE_CONFIG = """\
# ── Identity ─────────────────────────────────────────────────────────────────
clinic_id: "{clinic_id}"
name: "{name_he}"
name_en: ""
timezone: "Asia/Jerusalem"
language: "he"

# ── WhatsApp ──────────────────────────────────────────────────────────────────
whatsapp:
  number: "{whatsapp_number}"
  provider: "meta"
  meta_access_token: "${{META_ACCESS_TOKEN_{ENV_KEY}}}"
  meta_phone_number_id: "${{META_PHONE_NUMBER_ID_{ENV_KEY}}}"
  meta_verify_token: "${{META_VERIFY_TOKEN_{ENV_KEY}}}"

# ── AI Behavior ───────────────────────────────────────────────────────────────
ai:
  model: "gpt-4o"
  temperature: 0.3
  personality: |
    אתה נציג שירות לקוחות של {name_he}. ענה תמיד בעברית ברורה וקצרה.

# ── Calendar Backend ──────────────────────────────────────────────────────────
calendar:
  provider: "local_db"
  slot_duration_minutes: 60
  booking_window_days: 30
  min_notice_hours: 2

# ── Services ──────────────────────────────────────────────────────────────────
services:
  - id: "service1"
    name_he: "שירות ראשון"
    name_en: "First Service"
    duration_minutes: 60

# ── Working Hours ─────────────────────────────────────────────────────────────
working_hours:
  sunday:    {{ open: "09:00", close: "18:00" }}
  monday:    {{ open: "09:00", close: "18:00" }}
  tuesday:   {{ open: "09:00", close: "18:00" }}
  wednesday: {{ open: "09:00", close: "18:00" }}
  thursday:  {{ open: "09:00", close: "18:00" }}
  friday:    {{ open: "09:00", close: "14:00" }}
  saturday:  "closed"

# ── Notifications ─────────────────────────────────────────────────────────────
notifications:
  remind_hours_before: 24
  send_confirmation: true

# ── Human Handoff ─────────────────────────────────────────────────────────────
handoff:
  enabled: true
  trigger_keywords: ["אנוש", "נציג", "עזרה"]
  notify_phone: "+972500000000"
  message: "הועברת לנציג שירות. ניצור איתך קשר בהקדם."
"""

TEMPLATE_FAQS = """\
faqs:
  - id: "hours"
    keywords: ["שעות", "פתוח", "מתי פתוח"]
    question_he: "מה שעות הפתיחה?"
    answer_he: "שעות הפעילות שלנו: ראשון-חמישי 09:00-18:00, שישי 09:00-14:00."

  - id: "location"
    keywords: ["כתובת", "איפה", "מיקום"]
    question_he: "מה הכתובת שלכם?"
    answer_he: "אנחנו ממוקמים ב... (עדכן את הכתובת)"
"""


def create_clinic(clinic_id: str, name_he: str, whatsapp_number: str) -> None:
    clinics_dir = Path(__file__).parent.parent / "clinics"
    target = clinics_dir / clinic_id

    if target.exists():
        print(f"ERROR: Clinic folder already exists: {target}")
        sys.exit(1)

    target.mkdir(parents=True)
    env_key = clinic_id.upper().replace("-", "_")

    config_content = TEMPLATE_CONFIG.format(
        clinic_id=clinic_id,
        name_he=name_he,
        whatsapp_number=whatsapp_number,
        ENV_KEY=env_key,
    )

    (target / "config.yaml").write_text(config_content, encoding="utf-8")
    (target / "faqs.yaml").write_text(TEMPLATE_FAQS, encoding="utf-8")

    print(f"✅ Created clinic: {target}")
    print(f"\nAdd these to your .env file:")
    print(f"  META_ACCESS_TOKEN_{env_key}=EAAxxxxx")
    print(f"  META_PHONE_NUMBER_ID_{env_key}=1234567890")
    print(f"  META_VERIFY_TOKEN_{env_key}=your_verify_secret")
    print(f"\nThen edit: {target / 'config.yaml'}")
    print(f"And edit: {target / 'faqs.yaml'}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python -m scripts.create_new_clinic <clinic_id> <name_he> <whatsapp_number>")
        sys.exit(1)
    create_clinic(sys.argv[1], sys.argv[2], sys.argv[3])
