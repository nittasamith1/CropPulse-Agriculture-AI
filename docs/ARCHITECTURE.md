# Architecture Documentation

CropPulse is built as a modular, decoupled full-stack application.

## CropPulse – Architecture Overview

## High-Level Flow

```
Browser (Vanilla JS SPA)
  │
  │  HTTPS (JWT Bearer)
  ▼
FastAPI Backend (Render / Docker)
  ├─► Disease Router ──► DiseaseService ──► PyTorch EfficientNet-B0 ──► MongoDB
  ├─► Soil Router ────► SoilService ────► XGBoost / joblib ──────────► MongoDB
  ├─► Weather Router ─► WeatherService ─► Open-Meteo API (cached 30 min)
  ├─► Risk Router ────► RiskService ────► Multi-factor scoring engine ─► MongoDB
  ├─► Irrigation ─────► IrrigationService ► Rule + ML scheduler ───────► MongoDB
  ├─► Auth Router ─────► AuthService ────► bcrypt + JWT ──────────────► MongoDB
  ├─► Map Router ─────► MongoDB (GIS markers)
  ├─► History Router ─► MongoDB (prediction log)
  ├─► Reports Router ─► ReportService ──► WeasyPrint PDF ────────────► GridFS
  └─► Files Router ───► GridFS (image streaming)
```

## Component Layers

1. **Router Layer** (`backend/routers/`): Validates requests, enforces JWT auth, delegates to service.

2. **Service Layer** (`backend/services/`): Business logic, orchestration, no direct DB access.

3. **Repository Layer** (`backend/repositories/`): Thin async MongoDB CRUD wrappers using Motor.

4. **AI Layer** (`backend/ai/`):
   - `disease/model_manager.py` — Thread-safe singleton loader for EfficientNet-B0 `.pth` weights (PyTorch).
   - `disease/predictor.py` — Inference pipeline + Grad-CAM explainability.
   - `soil/model_manager.py` — Thread-safe singleton loader for XGBoost `.pkl` pipeline (joblib).
   - `soil/predictor.py` — Physics-informed fallback when model is absent.
   - `intelligence/recommendation_engine.py` — Agronomic knowledge base for disease/treatment/irrigation.

5. **Database** (`backend/database.py`): Motor async client → MongoDB Atlas. GridFS for binary storage.

6. **Auth Middleware** (`backend/middleware/auth_middleware.py`): JWT verification (python-jose / PyJWT).

## Technology Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.115 + Uvicorn |
| Auth | JWT (python-jose / PyJWT) + bcrypt |
| Disease AI | PyTorch 2.x + EfficientNet-B0 + Grad-CAM |
| Soil AI | XGBoost + scikit-learn (joblib pipeline) |
| Weather | Open-Meteo (free, no API key) |
| Database | MongoDB Atlas (Motor async driver) |
| File Storage | MongoDB GridFS |
| Frontend | Vanilla JS + Bootstrap 5 + Chart.js + Leaflet.js |
| Deployment | Backend → Render, Frontend → Vercel |
