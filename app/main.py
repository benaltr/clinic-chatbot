import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.webhooks import router as webhook_router
from app.core.config import settings
from app.tenants.registry import registry

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading clinic configurations from %s", settings.clinics_path)
    registry.load(settings.clinics_path)
    logger.info("Startup complete — %d clinic(s) registered", len(registry.all_configs()))
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Clinic WhatsApp Chatbot",
    description="Multi-tenant WhatsApp AI chatbot for health clinics (Hebrew)",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(webhook_router)


@app.get("/health")
async def health():
    return {"status": "ok", "clinics": len(registry.all_configs())}
