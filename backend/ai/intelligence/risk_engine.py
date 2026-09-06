"""
CropPulse – Crop Risk Intelligence Engine
Synthesizes disease detection, real-time weather, forecast, and soil moisture
into an explainable, multi-factor crop disease risk assessment.
"""

from typing import Dict, Any, List, Optional


class CropRiskEngine:
    """
    Evaluates cumulative disease and crop stress risk (0–100 score).
    """

    def evaluate_risk(
        self,
        disease_detected: bool = False,
        disease_severity: Optional[str] = None,
        disease_confidence: float = 0.0,
        temperature: float = 25.0,
        humidity: float = 65.0,
        precipitation_mm: float = 0.0,
        rain_probability_24h: float = 0.0,
        forecast_precipitation_24h: float = 0.0,
        soil_moisture: float = 40.0,
        crop_type: Optional[str] = None,
        historical_outbreaks_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Calculate composite risk score and generate clear, human-readable explanatory factors.

        Scoring Components:
        1. Leaf Disease Symptoms (Weight: 35)
        2. Ambient Weather Conduciveness (Weight: 25)
        3. 24-48h Rain & Moisture Forecast (Weight: 20)
        4. Soil Hydration & Root Stress (Weight: 20)
        """
        score = 0.0
        factors: List[str] = []

        # ── 1. Leaf Disease Factor (0–35 pts) ──────────────────────────────────
        disease_score = 0.0
        if disease_detected:
            sev = (disease_severity or "moderate").lower()
            if sev == "severe":
                disease_score = 35.0 * max(0.5, disease_confidence)
                factors.append("Severe disease symptoms identified on crop foliage")
            elif sev == "moderate":
                disease_score = 25.0 * max(0.5, disease_confidence)
                factors.append("Moderate disease symptoms detected on leaves")
            elif sev == "mild":
                disease_score = 15.0 * max(0.5, disease_confidence)
                factors.append("Early/mild disease symptoms detected")
        score += disease_score

        # ── 2. Ambient Weather Conduciveness (0–25 pts) ─────────────────────────
        weather_score = 0.0

        # Fungal pathogens thrive in high humidity (>=75%) and moderate warmth (18–28°C)
        if humidity >= 80:
            weather_score += 15.0
            factors.append(f"High relative humidity ({round(humidity)}%) creating favorable fungal spore environment")
        elif humidity >= 70:
            weather_score += 8.0
            factors.append(f"Elevated humidity ({round(humidity)}%) supports pathogen persistence")

        if 18 <= temperature <= 30:
            weather_score += 10.0
            factors.append(f"Optimal temperature ({round(temperature, 1)}°C) for disease propagation")
        elif temperature > 38:
            weather_score += 4.0
            factors.append(f"Heat stress condition ({round(temperature, 1)}°C)")
        elif temperature < 10:
            weather_score += 4.0
            factors.append(f"Cold stress condition ({round(temperature, 1)}°C)")

        score += min(25.0, weather_score)

        # ── 3. Weather Forecast & Rain (0–20 pts) ──────────────────────────────
        forecast_score = 0.0
        if forecast_precipitation_24h > 15.0 or rain_probability_24h >= 75:
            forecast_score += 20.0
            factors.append(f"Heavy rainfall forecast ({forecast_precipitation_24h:.1f} mm, {round(rain_probability_24h)}% probability) extends leaf wetness duration")
        elif forecast_precipitation_24h > 2.0 or rain_probability_24h >= 45:
            forecast_score += 12.0
            factors.append(f"Rain predicted within 24h ({round(rain_probability_24h)}% probability)")

        if precipitation_mm > 5.0:
            forecast_score += 5.0
            factors.append(f"Recent precipitation ({precipitation_mm:.1f} mm) increases splash dispersal")

        score += min(20.0, forecast_score)

        # ── 4. Soil Hydration & Root Stress (0–20 pts) ─────────────────────────
        soil_score = 0.0
        if soil_moisture > 75.0:
            soil_score += 15.0
            factors.append(f"Excessive soil moisture ({round(soil_moisture)}%) indicates waterlogging risk / root vulnerability")
        elif soil_moisture < 20.0:
            soil_score += 15.0
            factors.append(f"Severe soil moisture deficit ({round(soil_moisture)}%) causing water stress")

        if historical_outbreaks_count > 0:
            soil_score += 5.0
            factors.append(f"Historical disease recurrence observed in this plot ({historical_outbreaks_count} previous reports)")

        score += min(20.0, soil_score)

        # Final composite score clamped between 0 and 100
        final_score = int(round(min(100.0, max(0.0, score))))

        # Determine qualitative risk level
        if final_score >= 80:
            risk_level = "CRITICAL"
        elif final_score >= 60:
            risk_level = "HIGH"
        elif final_score >= 35:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        if not factors:
            factors.append("Environmental parameters and crop health indicators are stable and normal.")

        return {
            "risk_score": final_score,
            "risk_level": risk_level,
            "factors": factors,
            "breakdown": {
                "disease_factor": round(disease_score, 1),
                "weather_conduciveness": round(weather_score, 1),
                "forecast_factor": round(forecast_score, 1),
                "soil_stress_factor": round(soil_score, 1),
            },
            "disclaimer": "AI-generated risk score for agricultural decision-support only. Inspect crops on-site.",
        }


risk_engine = CropRiskEngine()
