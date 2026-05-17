import os
from pathlib import Path

import pytest

from app.tenants.loader import load_clinic


def test_load_demo_wellness_config():
    """Verify the demo_wellness YAML loads and validates correctly."""
    os.environ.setdefault("META_ACCESS_TOKEN", "test_token")
    os.environ.setdefault("META_PHONE_NUMBER_ID", "123456789")

    clinic_dir = Path(__file__).parent.parent / "clinics" / "demo_wellness"
    config = load_clinic(clinic_dir)

    assert config is not None
    assert config.clinic_id == "demo_wellness"
    assert config.name == "קליניקת האיזון"
    assert config.language == "he"
    assert len(config.services) == 4
    assert len(config.faqs) > 0
    assert config.working_hours["saturday"] == "closed"


def test_load_missing_config(tmp_path):
    """Returns None when config.yaml is missing."""
    config = load_clinic(tmp_path)
    assert config is None
