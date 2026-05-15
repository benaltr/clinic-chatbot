import logging
from pathlib import Path

from app.tenants.loader import load_all_clinics
from app.tenants.models import ClinicConfig

logger = logging.getLogger(__name__)


class ClinicRegistry:
    def __init__(self) -> None:
        self._by_number: dict[str, ClinicConfig] = {}
        self._by_id: dict[str, ClinicConfig] = {}

    def load(self, clinics_dir: Path) -> None:
        configs = load_all_clinics(clinics_dir)
        self._by_number = {}
        self._by_id = {}
        for config in configs:
            self._by_number[config.whatsapp.number] = config
            self._by_id[config.clinic_id] = config
        logger.info("Registry loaded: %d clinic(s)", len(configs))

    def get_by_number(self, number: str) -> ClinicConfig | None:
        return self._by_number.get(number)

    def get_by_id(self, clinic_id: str) -> ClinicConfig | None:
        return self._by_id.get(clinic_id)

    def all_configs(self) -> list[ClinicConfig]:
        return list(self._by_id.values())


registry = ClinicRegistry()
