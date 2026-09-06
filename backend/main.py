"""
CropPulse – AI-Powered Crop Intelligence Platform
FastAPI Application Entry Point.
Configures middleware, routers, CORS, rate limiting, structured logging, and lifespan events.
PyTorch EfficientNet-B0 + XGBoost + Open-Meteo + MongoDB Atlas.
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from loguru import logger

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.database import db
from backend.ai.disease.model_manager import disease_model_manager
from backend.ai.soil.model_manager import soil_model_manager
from backend.routers import (
    auth,
    disease,
    soil,
    weather,
    risk,
    irrigation,
    map_router,
    history,
    notifications,
    reports,
    admin,
    files,
)

# ── Logging Setup ─────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
os.makedirs(settings.UPLOAD_TEMP_DIR, exist_ok=True)
logger.remove()
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)
try:
    logger.add(settings.LOG_FILE, rotation="10 MB", retention="30 days", level=settings.LOG_LEVEL, enqueue=True)
except Exception:
    pass

# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW_SECONDS}seconds"],
)


# ── Lifespan Event ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management."""
    logger.info("🌿 CropPulse Crop Intelligence Platform starting up...")

    # 1. Connect database
    try:
        await db.connect()
        logger.info("✅ MongoDB Atlas client connected and indexed")
    except Exception as e:
        logger.warning(f"⚠️ Database connection not established at startup: {e}")

    # 2. Pre-load AI models once
    logger.info("🤖 Initializing AI Model Managers...")
    disease_model_manager.load_model()
    soil_model_manager.load_model()

    # 3. Create upload temp directory
    os.makedirs(settings.UPLOAD_TEMP_DIR, exist_ok=True)
    logger.info(f"✅ Upload directory ready: {settings.UPLOAD_TEMP_DIR}")

    yield

    # Shutdown
    await db.disconnect()
    logger.info("👋 CropPulse API shutting down...")


# ── FastAPI App Instance ──────────────────────────────────────────────────────
app = FastAPI(
    title="CropPulse API",
    description=(
        "CropPulse — Production-Grade AI Agricultural Intelligence Platform.\n\n"
        "Features:\n"
        "- 🍃 PyTorch EfficientNet-B0 Disease Detection with Grad-CAM\n"
        "- 🌦️ Open-Meteo Weather Intelligence & Forecast Caching\n"
        "- 💧 Tabular Machine Learning Soil Moisture Prediction\n"
        "- ⚠️ Multi-Factor Crop Disease Risk Assessment Engine\n"
        "- 🚜 Precision Irrigation Recommendation Engine\n"
        "- 🗺️ GIS Geospatial Farm Health Monitoring\n"
    ),
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect",
)

# ── Rate Limiter State ────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Static Files Mount ────────────────────────────────────────────────────────
try:
    app.mount("/static/uploads", StaticFiles(directory=settings.UPLOAD_TEMP_DIR), name="uploads")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


# ── Structured Request Logging & Timing Middleware ────────────────────────────
@app.middleware("http")
async def log_and_time_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(f"← {response.status_code} {request.url.path} ({duration_ms}ms)")
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    return response


# ── Centralized Exception Handlers ────────────────────────────────────────────
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return standardized API error payload for all HTTP status codes."""
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": detail},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(detail),
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return standardized API validation error payload."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": exc.errors(),
            },
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all unhandled exception handler."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred. Please try again later.",
            },
        },
    )


# ── Router Registration ───────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router,          prefix=f"{API_PREFIX}/auth",          tags=["Authentication"])
app.include_router(disease.router,       prefix=f"{API_PREFIX}/disease",       tags=["Disease Detection (PyTorch)"])
app.include_router(soil.router,          prefix=f"{API_PREFIX}/soil",          tags=["Soil Moisture Prediction"])
app.include_router(weather.router,       prefix=f"{API_PREFIX}/weather",       tags=["Weather Intelligence (Open-Meteo)"])
app.include_router(risk.router,          prefix=f"{API_PREFIX}/risk",          tags=["Crop Disease Risk Engine"])
app.include_router(irrigation.router,    prefix=f"{API_PREFIX}/irrigation",    tags=["Precision Irrigation"])
app.include_router(map_router.router,    prefix=f"{API_PREFIX}/map",           tags=["GIS Farm Monitoring"])
app.include_router(history.router,       prefix=f"{API_PREFIX}/history",       tags=["Unified History"])
app.include_router(notifications.router, prefix=f"{API_PREFIX}/notifications", tags=["Notifications & Alerts"])
app.include_router(reports.router,       prefix=f"{API_PREFIX}/reports",       tags=["PDF Reports (ReportLab)"])
app.include_router(admin.router,         prefix=f"{API_PREFIX}/admin",         tags=["Admin Management"])
app.include_router(files.router,         prefix=f"{API_PREFIX}/files",         tags=["File Storage (GridFS)"])


# ── Root & System Health Endpoints ───────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "platform": "CropPulse AI Agricultural Intelligence Platform",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/api/docs",
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """System health check verifying database and AI subsystem statuses."""
    db_ok = False
    if db.client:
        try:
            await db.client.admin.command("ping")
            db_ok = True
        except Exception:
            db_ok = False

    disease_meta = disease_model_manager.get_metadata()
    soil_meta = soil_model_manager.get_metadata()

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": time.time(),
        "database": {"connected": db_ok, "engine": "MongoDB Atlas"},
        "subsystems": {
            "disease_ai": disease_meta,
            "soil_ml": soil_meta,
            "weather_service": "active",
        },
    }
