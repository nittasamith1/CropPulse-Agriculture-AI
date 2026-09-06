# CropPulse Deployment Guide

## Stack

| Layer | Service | Cost |
|---|---|---|
| Backend API | [Render](https://render.com) Web Service | Free |
| Database | [MongoDB Atlas](https://cloud.mongodb.com) M0 Cluster | Free |
| Frontend | [Vercel](https://vercel.com) | Free |
| File Storage | MongoDB GridFS (same Atlas cluster) | Free |

---

## 1. MongoDB Atlas Setup

You already have a cluster at `cluster0.xdax7ct.mongodb.net`. Make sure:

1. **Network Access** → Add `0.0.0.0/0` to allow access from Render's IPs
2. **Database Access** → Your user `db_user` has `readWrite` on `CropPulse` DB
3. The connection string format should be:
   ```
   mongodb+srv://db_user:<password>@cluster0.xdax7ct.mongodb.net/?appName=Cluster0
   ```

---

## 2. Deploy Backend to Render

### Option A: render.yaml (recommended)
1. Push your code to GitHub
2. Go to [render.com/dashboard](https://dashboard.render.com) → **New → Blueprint**
3. Connect your GitHub repo — Render reads `render.yaml` automatically
4. Set these **environment variables** in the Render dashboard:
   - `MONGODB_URI` → your Atlas URI
   - `SECRET_KEY` → a random 32+ character string (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
5. Deploy → your API will be live at `https://croppulse-agriculture-ai.onrender.com`

### Option B: Manual
1. **New Web Service** → Connect GitHub repo
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Python Version:** 3.11
5. Add all env vars from `.env.example`

### Verify Backend
```bash
curl https://croppulse-agriculture-ai.onrender.com/api/health
# → {"status":"healthy","database":"connected",...}
```

---

## 3. Deploy Frontend to Vercel

### Step 1: Update API URL
Edit `frontend/assets/js/api.js` line ~13:
```js
const RENDER_BACKEND = "https://croppulse-agriculture-ai.onrender.com";
```

### Step 2: Update vercel.json
Edit `vercel.json` to point the API proxy to your real Render URL:
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://croppulse-agriculture-ai.onrender.com/api/:path*"
    }
  ]
}
```

### Step 3: Deploy
1. Go to [vercel.com](https://vercel.com) → **New Project** → Import GitHub repo
2. **Root Directory** → Set to `frontend/`
3. **Framework Preset** → Other
4. Deploy → your frontend is live at `https://crop-pulse-agriculture-ai.vercel.app`

---

## 4. Docker (Self-hosted / VPS)

For deploying on a VPS (DigitalOcean, AWS EC2, etc.):

```bash
# Clone repo
git clone https://github.com/youruser/CropPulse.git
cd CropPulse

# Create .env from example
cp .env.example .env
# Edit .env with your real MongoDB Atlas URI and SECRET_KEY

# Build and run
docker compose up -d --build

# Check logs
docker compose logs -f backend
```

The backend will be at `http://your-server-ip:8000`

---

## 5. Adding AI Models

The app runs in **stub mode** until real models are provided.

### Disease Model
Place your trained EfficientNet-B0 PyTorch model at:
```
ai_models/disease_model/disease_model.pth
```
Expected: PyTorch state dict with 38-class EfficientNet-B0 output.

### Soil Model
Place your trained sklearn/XGBoost pipeline at:
```
ai_models/soil_model/soil_model.pkl
```
Expected: joblib-serialized pipeline with `predict([[temp, humidity, rainfall, wind_speed, soil_idx, prev_moisture]])`.

---

## 6. Email (SMTP) Setup

To enable password-reset and verification emails, set in `.env`:
```
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password    # Gmail App Password (not regular password)
EMAIL_FROM=noreply@CropPulse.ai
```

> **Tip:** For Gmail, enable 2FA and generate an App Password at https://myaccount.google.com/apppasswords

---

## 7. Environment Variables Reference

Copy `.env.example` and fill in:

```env
# Core
APP_NAME=CropPulse
APP_ENV=production
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">

# MongoDB Atlas
MONGODB_URI=mongodb+srv://db_user:PASSWORD@cluster0.xdax7ct.mongodb.net/?appName=Cluster0
MONGODB_DB_NAME=CropPulse

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# SMTP (optional)
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# CORS (comma-separated; * for dev only)
ALLOWED_ORIGINS=https://crop-pulse-agriculture-ai.vercel.app,http://localhost:8080

# Logging
LOG_LEVEL=INFO
```
