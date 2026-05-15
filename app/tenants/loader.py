import logging
from pathlib import Path

import yaml

from app.tenants.models import ClinicConfig, FAQItem

logger = logging.getLogger(__name__)


def load_clinic(clinic_dir: Path) -> ClinicConfig | None:
    config_path = clinic_dir / "config.yaml"
    if not config_path.exists():
        logger.warning("No config.yaml found in %s — skipping", clinic_dir)
        return None

    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Merge faqs from separate faqs.yaml if it exists
    faqs_path = clinic_dir / "faqs.yaml"
    if faqs_path.exists():
        with faqs_path.open(encoding="utf-8") as f:
            faqs_raw = yaml.safe_load(f) or {}
        raw["faqs"] = faqs_raw.get("faqs", [])

    try:
        config = ClinicConfig.model_validate(raw)
        logger.info("Loaded clinic config: %s (%s)", config.clinic_id, config.name)
        return config
    except Exception as exc:
        logger.error("Invalid config in %s: %s", clinic_dir, exc)
        return None


def load_all_clinics(clinics_dir: Path) -> list[ClinicConfig]:
    if not clinics_dir.exists():
        logger.warning("Clinics directory not found: %s", clinics_dir)
        return []

    configs = []
    for entry in sorted(clinics_dir.iterdir()):
        if entry.is_dir():
            config = load_clinic(entry)
            if config:
                configs.append(config)

    logger.info("Loaded %d clinic config(s)", len(configs))
    return configs
