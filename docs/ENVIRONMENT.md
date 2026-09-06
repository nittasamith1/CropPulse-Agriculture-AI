# CropPulse – Environment Variables Reference

The `.env` file is crucial for the CropPulse application. It contains secrets and configuration for MongoDB, JWT auth, AI models, SMTP email, and CORS.

Copy `.env.example` → `.env` and fill in the values. **Never commit `.env` to version control.**

---

## Required Variables

| Variable | Description | Example |
|---|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `MONGODB_DB_NAME` | Database name | `croppulse` |
| `SECRET_KEY` | JWT signing secret (32+ chars, random) | `openssl rand -hex 32` |

---

## AI Model Paths

| Variable | Description | Default |
|---|---|---|
| `DISEASE_MODEL_PATH` | Path to EfficientNet-B0 `.pth` weights | `ai_models/disease_model/disease_model.pth` |
| `SOIL_MODEL_PATH` | Path to XGBoost/sklearn `.pkl` pipeline | `ai_models/soil_model/soil_model.pkl` |

> When model files are absent, the platform runs in **stub mode** and clearly labels responses with `stub_mode: true`.

---

## JWT Configuration

| Variable | Description | Default |
|---|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `30` |

---

## Email (SMTP) — Optional

| Variable | Description |
|---|---|
| `EMAIL_ENABLED` | Set to `true` to enable SMTP email |
| `SMTP_HOST` | SMTP server hostname (e.g., `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (default: `587`) |
| `SMTP_USER` | SMTP sender email address |
| `SMTP_PASSWORD` | SMTP password or app-specific password |
| `FROM_EMAIL` | Sender display email |

---

## CORS & Server

| Variable | Description | Default |
|---|---|---|
| `ALLOWED_ORIGINS` | Comma-separated list of allowed origins | `http://localhost:8080` |
| `LOG_LEVEL` | Log verbosity: `DEBUG`, `INFO`, `WARNING` | `INFO` |

---

## Example `.env`

```ini
# -- Required ------------------------------------------------------------------
MONGODB_URI=mongodb+srv://myuser:mypassword@cluster0.abc.mongodb.net/
MONGODB_DB_NAME=croppulse
SECRET_KEY=change_me_to_a_32_char_random_string

# -- AI Models -----------------------------------------------------------------
DISEASE_MODEL_PATH=ai_models/disease_model/disease_model.pth
SOIL_MODEL_PATH=ai_models/soil_model/soil_model.pkl

# -- JWT -----------------------------------------------------------------------
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# -- Email (optional) ----------------------------------------------------------
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@croppulse.com

# -- CORS ----------------------------------------------------------------------
ALLOWED_ORIGINS=http://localhost:8080,https://your-app.vercel.app

# -- Logging -------------------------------------------------------------------
LOG_LEVEL=INFO
```
