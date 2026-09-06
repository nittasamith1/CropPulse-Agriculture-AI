# CropPulse API Reference

The CropPulse backend exposes a REST API via FastAPI.
The base prefix for all endpoints is `/api/v1`.

Interactive Swagger UI documentation is available at `/api/docs` and ReDoc at `/api/redoc`.

---

## Authentication & Users (`/api/v1/auth`)

### 1. Register User
- **URL**: `/api/v1/auth/register`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "email": "farmer@example.com",
    "password": "securepassword123",
    "name": "Samith Nitta",
    "role": "farmer",
    "phone": "+919876543210",
    "state": "Andhra Pradesh",
    "district": "Chittoor"
  }
  ```
- **Response**: `201 Created`

### 2. Login (Password)
- **URL**: `/api/v1/auth/login`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "email": "farmer@example.com",
    "password": "securepassword123"
  }
  ```
- **Response**: `200 OK` (returns `access_token`, `refresh_token`, `token_type`, `user`)

### 3. Refresh Access Token
- **URL**: `/api/v1/auth/refresh`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "refresh_token": "<REFRESH_TOKEN>"
  }
  ```
- **Response**: `200 OK` (returns new `access_token` and `refresh_token`)

### 4. Logout
- **URL**: `/api/v1/auth/logout`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Payload**:
  ```json
  {
    "refresh_token": "<REFRESH_TOKEN>"
  }
  ```
- **Response**: `200 OK`

### 5. Forgot Password
- **URL**: `/api/v1/auth/forgot-password`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "email": "farmer@example.com"
  }
  ```
- **Response**: `200 OK`

### 6. Reset Password
- **URL**: `/api/v1/auth/reset-password`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "token": "<RESET_TOKEN>",
    "new_password": "newsecurepassword123"
  }
  ```
- **Response**: `200 OK`

### 7. Get Current User Profile
- **URL**: `/api/v1/auth/me`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Response**: `200 OK`

---

## Disease Detection (`/api/v1/disease`)

### 1. Detect Crop Leaf Disease
- **URL**: `/api/v1/disease/detect` (or alias `/api/v1/disease/predict`)
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Payload**: `multipart/form-data`
  - `file`: Image binary (JPG, PNG, WEBP, BMP up to 10MB)
  - `farm_id`: Optional string
  - `crop_type`: Optional string
  - `latitude`: Optional float (-90 to 90)
  - `longitude`: Optional float (-180 to 180)
  - `notes`: Optional string
- **Response**: `201 Created`
  ```json
  {
    "success": true,
    "prediction_id": "dpred_abc123",
    "disease_name": "Tomato – Early blight",
    "disease_class_key": "Tomato___Early_blight",
    "crop_type": "Tomato",
    "confidence": 0.9421,
    "severity": "severe",
    "is_healthy": false,
    "treatments": ["Apply contact fungicide...", "Prune lower leaves..."],
    "prevention_tips": ["Crop rotation...", "Drip irrigation..."],
    "recommended_pesticides": ["Mancozeb", "Chlorothalonil"],
    "organic_remedies": ["Copper octanoate", "Neem oil"],
    "top_3": [...],
    "explanation_available": true,
    "explanation_data_uri": "data:image/jpeg;base64,...",
    "model_version": "1.0.0"
  }
  ```

### 2. Disease Scan History
- **URL**: `/api/v1/disease/history`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Query Params**: `page=1`, `page_size=20`, `farm_id` (optional)
- **Response**: `200 OK` (paginated list)

### 3. Get Single Disease Prediction
- **URL**: `/api/v1/disease/{prediction_id}`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Response**: `200 OK`

---

## Soil Moisture Intelligence (`/api/v1/soil`)

### 1. Predict Soil Moisture
- **URL**: `/api/v1/soil/predict`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Payload**:
  ```json
  {
    "temperature": 28.5,
    "humidity": 55.0,
    "rainfall": 12.0,
    "soil_temperature": 24.2,
    "wind_speed": 4.1,
    "soil_type": "loamy",
    "crop_type": "Tomato",
    "farm_id": "farm_123",
    "latitude": 13.52,
    "longitude": 79.98
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "success": true,
    "soil_prediction_id": "spred_xyz789",
    "predicted_moisture_percent": 34.5,
    "moisture_status": "Adequate",
    "irrigation_needed": false,
    "recommended_water_amount_mm": 0.0,
    "model_type": "XGBoost Regressor / Random Forest",
    "model_version": "1.0.0"
  }
  ```

### 2. Soil Prediction History
- **URL**: `/api/v1/soil/history`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Query Params**: `page=1`, `page_size=20`, `farm_id` (optional)
- **Response**: `200 OK`

---

## Weather Intelligence (`/api/v1/weather`)

### 1. Current Weather & Forecast
- **URL**: `/api/v1/weather`
- **Method**: `GET`
- **Query Params**: `latitude=13.52&longitude=79.98`
- **Response**: `200 OK` (current conditions, 7-day hourly and daily forecast cached for 30m)

### 2. Agricultural Weather Summary
- **URL**: `/api/v1/weather/summary`
- **Method**: `GET`
- **Query Params**: `latitude=13.52&longitude=79.98`
- **Response**: `200 OK` (evapotranspiration, GDD, heat index, frost risk)

---

## Precision Irrigation Advisory (`/api/v1/irrigation`)

### 1. Get Precision Irrigation Recommendation
- **URL**: `/api/v1/irrigation/advisory`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Payload**: Farm location, soil characteristics, crop stage, and recent rainfall.
- **Response**: `200 OK` (water volume, duration, method recommendation)

---

## Crop Risk Intelligence (`/api/v1/risk`)

### 1. Calculate Multi-Factor Crop Risk
- **URL**: `/api/v1/risk/calculate`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Payload**: Crop parameters, disease history, weather signals, soil conditions.
- **Response**: `200 OK` (risk index 0-100, risk level, contributing factors, mitigation actions)

---

## Geospatial Intelligence (`/api/v1/map`)

### 1. Disease Outbreaks & Soil Moisture Map Data
- **URL**: `/api/v1/map/hotspots`
- **Method**: `GET`
- **Query Params**: `crop_type`, `state`, `district`, `radius_km`
- **Response**: `200 OK` (GeoJSON feature collection of active outbreaks and farm clusters)

---

## Reports & Exports (`/api/v1/reports`)

### 1. Generate PDF Report
- **URL**: `/api/v1/reports/pdf`
- **Method**: `POST`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Payload**: Report options (start_date, end_date, farm_id)
- **Response**: `200 OK` (binary PDF download stream)

### 2. Export CSV Data
- **URL**: `/api/v1/reports/csv`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Query Params**: `category=disease|soil|all`
- **Response**: `200 OK` (text/csv stream)

---

## File Storage (`/api/v1/files`)

### 1. Retrieve Stored File
- **URL**: `/api/v1/files/{file_id}`
- **Method**: `GET`
- **Response**: `200 OK` (binary stream from MongoDB GridFS with appropriate Content-Type)

---

## Admin Operations (`/api/v1/admin`)

*All admin endpoints require an active token with `role: "admin"`.*

### 1. Platform Analytics
- **URL**: `/api/v1/admin/analytics`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <ADMIN_TOKEN>`
- **Response**: `200 OK` (aggregate stats, active users, scans count, disease distribution)

### 2. User Management
- **URL**: `/api/v1/admin/users`
- **Method**: `GET`
- **Headers**: `Authorization: Bearer <ADMIN_TOKEN>`
- **Query Params**: `page=1`, `page_size=20`, `search` (optional)
- **Response**: `200 OK`

### 3. Update User Status
- **URL**: `/api/v1/admin/users/{user_id}/status`
- **Method**: `PATCH`
- **Headers**: `Authorization: Bearer <ADMIN_TOKEN>`
- **Payload**: `{"is_active": false}`
- **Response**: `200 OK`
