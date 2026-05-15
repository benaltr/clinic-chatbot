"""
Seed the demo_wellness clinic and its services into the database.
Run after: alembic upgrade head
Usage: python -m scripts.seed_demo_clinic
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import Clinic, Service
from app.tenants.loader import load_clinic


async def seed() -> None:
    engine = create_async_engine(settings.database_url, echo=True)
    AsyncSession_ = async_sessionmaker(engine, expire_on_commit=False)

    clinic_dir = settings.clinics_path / "demo_wellness"
    config = load_clinic(clinic_dir)
    if config is None:
        print("ERROR: Could not load demo_wellness config")
        return

    async with AsyncSession_() as db:
        # Upsert clinic
        result = await db.execute(select(Clinic).where(Clinic.slug == config.clinic_id))
        clinic = result.scalar_one_or_none()
        if clinic is None:
            clinic = Clinic(
                slug=config.clinic_id,
                name=config.name,
                whatsapp_number=config.whatsapp.number,
                timezone=config.timezone,
            )
            db.add(clinic)
            await db.flush()
            print(f"Created clinic: {clinic.name} ({clinic.id})")
        else:
            print(f"Clinic already exists: {clinic.name} ({clinic.id})")

        # Upsert services
        for svc in config.services:
            existing = await db.execute(
                select(Service).where(
                    Service.clinic_id == clinic.id,
                    Service.service_key == svc.id,
                )
            )
            if existing.scalar_one_or_none() is None:
                db.add(Service(
                    clinic_id=clinic.id,
                    service_key=svc.id,
                    name_he=svc.name_he,
                    name_en=svc.name_en,
                    duration_minutes=svc.duration_minutes,
                ))
                print(f"  Added service: {svc.name_he}")

        await db.commit()
        print("Seed complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
