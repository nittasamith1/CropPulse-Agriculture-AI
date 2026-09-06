# Installation & Local Setup

Follow these instructions to set up the CropPulse development environment.

## Prerequisites

1. **Python 3.11** or higher.
2. **MongoDB Atlas** account or local MongoDB 6.0+ instance.
3. **Git** for version control.

---

## Installation Steps

### 1. Clone & Navigate
```bash
git clone <repository_url> CropPulse
cd CropPulse
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate   # On Windows
source .venv/bin/activate  # On Linux/macOS
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your configuration:
```bash
cp .env.example .env
```

Key environment variables:
```env
APP_NAME=CropPulse
APP_ENV=development
APP_PORT=8000
FRONTEND_URL=http://localhost:8080

# Security (generate a secure 64-char key for production)
SECRET_KEY=your-random-64-character-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# MongoDB Atlas
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?appName=CropPulse
MONGODB_DB_NAME=croppulse

# AI Model Paths
DISEASE_MODEL_PATH=./ai_models/disease_model/disease_model.pth
SOIL_MODEL_PATH=./ai_models/soil_model/soil_model.pkl
DISEASE_CLASSES_PATH=./datasets/disease/disease_labels.csv
MODEL_CONFIDENCE_THRESHOLD=0.65

# Weather (Open-Meteo free API)
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1
WEATHER_CACHE_TTL_SECONDS=1800
```

### 5. AI Models Setup
Place or generate your model artifacts:
- **PyTorch Disease Model**: `ai_models/disease_model/disease_model.pth`
- **XGBoost Soil Model**: `ai_models/soil_model/soil_model.pkl`

To train or test the soil model:
```bash
python -m ai_models.soil_model.train_soil_model
```

### 6. Running the Backend
```bash
uvicorn backend.main:app --reload --port 8000
```
Interactive API documentation will be available at `http://localhost:8000/api/docs`.

### 7. Serving the Frontend
Serve the `frontend/` directory using any local HTTP static server:
```bash
python -m http.server 8080 --directory frontend
```
Navigate to `http://localhost:8080` in your web browser.

### 8. Running the Automated Test Suite
```bash
pytest tests/ -v
```
