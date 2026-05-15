import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.routes import router as v1_router
from app.config import settings
from app.utils.logger import get_logger

class _HealthFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "GET /health" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(_HealthFilter())

logger = get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EHDS Pipeline Backend...")
    # Startup: could initialize database connections or verify FHIR server connectivity
    yield
    logger.info("Shutting down EHDS Pipeline Backend...")
    pass

app = FastAPI(
    title="EHDS Pipeline Backend",
    description="Pipeline for extracting clinical data into FHIR R4 Bundles (EEHRxF compliant)",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(v1_router, prefix="/api/v1")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to the exact frontend domain!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    logger.debug("Health check requested.")
    return {"status": "ok", "environment": settings.environment}
