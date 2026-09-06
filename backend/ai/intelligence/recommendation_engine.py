"""
CropPulse – Precision Recommendation Engine
Generates agronomic disease treatments and precision irrigation decision-support recommendations.
"""

from typing import Dict, List, Any, Optional

# ── Agronomic Disease Knowledgebase ───────────────────────────────────────────
DISEASE_DATABASE = {
    "Apple_scab": {
        "treatments": [
            "Apply sulfur-based fungicides every 10-14 days",
            "Use copper fungicides during dormant season",
            "Remove infected leaves and fallen fruit",
        ],
        "prevention": [
            "Prune canopy to improve air circulation",
            "Avoid overhead sprinkler watering to reduce leaf wetness",
            "Select scab-resistant apple cultivars",
            "Apply clean organic mulch around base to prevent ascospore splash",
        ],
        "pesticides": ["Sulfur dust", "Copper sulfate", "Captan fungicide", "Myclobutanil"],
        "organic": ["Neem oil spray (0.5%)", "Potassium bicarbonate solution", "Dilute milk spray (1:9 ratio)"],
    },
    "Potato_early_blight": {
        "treatments": [
            "Apply contact fungicide (e.g. Mancozeb) on 7–10 day intervals",
            "Remove and safely dispose of severely necrotic lower foliage",
            "Ensure uniform soil moisture to avoid tuber cracking",
        ],
        "prevention": [
            "Use certified pathogen-free seed tubers",
            "Practice minimum 2-year crop rotation with non-solanaceous crops",
            "Eliminate nightshade weeds and volunteer potato plants",
            "Avoid excessive overhead irrigation late in the day",
        ],
        "pesticides": ["Mancozeb", "Chlorothalonil", "Copper hydroxide", "Azoxystrobin"],
        "organic": ["Bacillus subtilis bio-fungicide", "Copper octanoate", "Trichoderma harzianum soil inoculant"],
    },
    "Potato_late_blight": {
        "treatments": [
            "Immediately apply systemic fungicide with anti-sporulant action",
            "Prune infected foliage during dry afternoon hours",
            "If infestation exceeds 50%, harvest early or destroy haulms to protect tubers",
        ],
        "prevention": [
            "Plant late blight-resistant potato varieties",
            "Ensure hill ridges are adequate to prevent tuber contact with spores",
            "Maintain wide plant spacing for rapid canopy drying",
        ],
        "pesticides": ["Metalaxyl + Mancozeb", "Cymoxanil", "Dimethomorph", "Chlorothalonil"],
        "organic": ["Fixed copper sprays", "Bordeaux mixture", "Bacillus amyloliquefaciens"],
    },
    "Tomato_early_blight": {
        "treatments": [
            "Prune infected bottom leaves up to 30cm from soil level",
            "Apply protective fungicide focusing on underside of leaves",
            "Stake or trellis indeterminate vines off the soil",
        ],
        "prevention": [
            "Apply thick organic or plastic mulch to eliminate soil splash",
            "Utilize drip irrigation exclusively",
            "Rotate tomato plots with brassicas or legumes every 3 seasons",
        ],
        "pesticides": ["Chlorothalonil", "Mancozeb", "Copper oxychloride", "Difenoconazole"],
        "organic": ["Copper soap fungicide", "Bacillus subtilis strain QST 713", "Neem oil extract"],
    },
    "Tomato_late_blight": {
        "treatments": [
            "Remove and bag affected plant clusters immediately",
            "Apply translaminar / systemic fungicide during early dawn before sun heats leaves",
            "Disinfect pruning shears with 70% isopropyl alcohol between cuts",
        ],
        "prevention": [
            "Ensure excellent greenhouse ventilation or open-field air drainage",
            "Avoid planting downwind from potato fields",
            "Use drip irrigation lines buried under mulch",
        ],
        "pesticides": ["Metalaxyl-M", "Mandipropamid", "Cymoxanil", "Chlorothalonil"],
        "organic": ["Copper hydroxide", "Liquid copper fungicide", "Potassium bicarbonate"],
    },
    "Tomato_yellow_leaf_curl": {
        "treatments": [
            "Rogue and bury severely infected stunted plants immediately",
            "Install yellow sticky cards to trap whitefly vectors",
            "Apply systemic insecticide to manage Bemisia tabaci vector populations",
        ],
        "prevention": [
            "Use 50-mesh insect-proof netting in seedling nurseries",
            "Plant TYLCV-resistant hybrid tomato seeds",
            "Avoid planting adjacent to older cucurbit or solanaceous plantings",
        ],
        "pesticides": ["Imidacloprid", "Thiamethoxam", "Acetamiprid", "Spiromesifen"],
        "organic": ["Insecticidal soap", "Cold-pressed neem oil", "Beauveria bassiana bio-insecticide"],
    },
    "Healthy": {
        "treatments": [
            "Continue standard monitoring and agronomic regimen",
            "Maintain consistent balanced nutrient delivery (NPK + micronutrients)",
            "Inspect underside of foliage weekly for emerging pest pressure",
        ],
        "prevention": [
            "Maintain optimal crop spacing and drip irrigation schedules",
            "Scout perimeter rows twice weekly",
            "Encourage beneficial predator insects (ladybugs, lacewings)",
        ],
        "pesticides": ["No chemical treatment needed - plant foliage is healthy"],
        "organic": ["Apply well-composted organic matter to promote microbial vitality"],
    },
}

CROP_MAPPING = {
    "apple": "Apple",
    "blueberry": "Blueberry",
    "cherry": "Cherry",
    "corn": "Corn",
    "grape": "Grape",
    "orange": "Orange",
    "peach": "Peach",
    "pepper": "Pepper",
    "potato": "Potato",
    "raspberry": "Raspberry",
    "soybean": "Soybean",
    "squash": "Squash",
    "strawberry": "Strawberry",
    "tomato": "Tomato",
}

# Crop coefficient Kc per FAO-56 (source: FAO Irrigation and Drainage Paper 56, Table 12)
CROP_KC_VALUES = {
    "tomato":      {"initial": 0.60, "mid": 1.15, "late": 0.80},
    "potato":      {"initial": 0.50, "mid": 1.15, "late": 0.75},
    "corn":        {"initial": 0.30, "mid": 1.20, "late": 0.50},
    "maize":       {"initial": 0.30, "mid": 1.20, "late": 0.50},
    "wheat":       {"initial": 0.30, "mid": 1.15, "late": 0.40},
    "pepper":      {"initial": 0.60, "mid": 1.05, "late": 0.90},
    "grape":       {"initial": 0.30, "mid": 0.85, "late": 0.45},
    "apple":       {"initial": 0.45, "mid": 1.20, "late": 0.75},
    "strawberry":  {"initial": 0.40, "mid": 0.85, "late": 0.75},
    "soybean":     {"initial": 0.40, "mid": 1.15, "late": 0.50},
}

# Soil water parameters per soil type
# (field_capacity %, wilting_point %, root_zone_depth_mm, application_efficiency)
SOIL_PARAMS = {
    "sandy":    {"fc": 20.0, "wp": 8.0,  "rzd": 400, "efficiency": 0.80},
    "loamy":    {"fc": 35.0, "wp": 16.0, "rzd": 600, "efficiency": 0.85},
    "clay":     {"fc": 45.0, "wp": 25.0, "rzd": 600, "efficiency": 0.75},
    "peaty":    {"fc": 55.0, "wp": 30.0, "rzd": 500, "efficiency": 0.80},
    "silt":     {"fc": 38.0, "wp": 18.0, "rzd": 600, "efficiency": 0.82},
    "silty":    {"fc": 38.0, "wp": 18.0, "rzd": 600, "efficiency": 0.82},
}

# Allowable depletion fraction (p) per FAO-56
# Fraction of TAW that can be depleted before irrigation stress occurs
ALLOWABLE_DEPLETION_FRACTION = 0.50


class PrecisionIrrigationEngine:
    """
    Computes precision irrigation recommendations using a transparent water-balance model
    based on FAO-56 methodology:
      TAW  = (FC - WP) × Root-Zone-Depth
      RAW  = TAW × p           (Readily Available Water)
      Depletion = (FC - SM) × RZD
      ETc  = ET0 × Kc
      Net_irrigation = max(0, Depletion - Effective_rain + ETc_daily)
      Gross_irrigation = Net_irrigation / efficiency
      Litres/ha = Gross_irrigation × 10,000

    Decision hierarchy (priority order):
      1. Soil is over-saturated → REDUCE_IRRIGATION
      2. Depletion > RAW and rain cannot cover → IRRIGATE
      3. Depletion <= RAW and significant rain expected → WAIT
      4. Soil near optimal → MONITOR
    """

    def generate_recommendation(
        self,
        soil_moisture: float,
        temperature: float,
        humidity: float,
        rain_probability_24h: float = 0.0,
        forecast_precipitation_24h: float = 0.0,
        crop_type: Optional[str] = None,
        growth_stage: str = "mid",
        recent_rainfall_mm: float = 0.0,
        soil_type: str = "loamy",
        et0_mm: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate decision: IRRIGATE | WAIT | REDUCE_IRRIGATION | MONITOR

        Args:
            soil_moisture:             Current volumetric water content (%).
            temperature:               Air temperature (°C).
            humidity:                  Relative humidity (%).
            rain_probability_24h:      Probability of rain in next 24h (0-100).
            forecast_precipitation_24h: Forecast precipitation next 24h (mm).
            crop_type:                 Crop name (e.g. 'tomato').
            growth_stage:              'initial' | 'mid' | 'late'.
            recent_rainfall_mm:        Rainfall in last 24h (mm).
            soil_type:                 Soil classification (loamy, sandy, clay, peaty).
            et0_mm:                    Reference ET₀ from Open-Meteo forecast (mm/day).
                                       If None, estimated from temperature/humidity.
        """
        crop_key = (crop_type or "tomato").lower().strip()
        s_type = soil_type.lower().strip()
        stage = growth_stage.lower().strip()

        # ── Crop Coefficient ──────────────────────────────────────────────────
        kc = CROP_KC_VALUES.get(crop_key, CROP_KC_VALUES["tomato"]).get(stage, 1.0)

        # ── Soil Parameters ───────────────────────────────────────────────────
        soil = SOIL_PARAMS.get(s_type, SOIL_PARAMS["loamy"])
        fc   = soil["fc"]          # Field capacity (%)
        wp   = soil["wp"]          # Wilting point (%)
        rzd  = soil["rzd"]         # Root-zone depth (mm)
        eff  = soil["efficiency"]  # Application efficiency

        # ── Water Balance Calculation ─────────────────────────────────────────
        # Total Available Water (mm) in root zone
        taw = (fc - wp) * rzd / 100.0
        # Readily Available Water (mm) — irrigation triggers when depletion > RAW
        p = ALLOWABLE_DEPLETION_FRACTION
        raw = taw * p

        # Current root-zone depletion (mm)
        depletion = max(0.0, (fc - soil_moisture) * rzd / 100.0)

        # ET₀ estimation: use Open-Meteo value if available, else simple Hargreaves-style estimate
        if et0_mm is not None and et0_mm > 0:
            et0 = float(et0_mm)
            et0_estimated = False
        else:
            # Simplified Blaney-Criddle style estimate from temp/humidity
            # Not precise — will be flagged as estimated
            vpd = max(0.0, (1 - humidity / 100.0) * 0.6108 * 2.718 ** (17.27 * temperature / (temperature + 237.3)))
            et0 = max(0.5, 0.0023 * (temperature + 17.8) * (temperature - temperature * 0.5) ** 0.5 * 0.408 + vpd * 0.2)
            et0 = min(et0, 9.0)  # cap at realistic maximum
            et0_estimated = True

        # Crop water demand today (mm)
        etc = round(et0 * kc, 2)

        # Effective rainfall (mm):
        # Open-Meteo precipitation_sum is the EXPECTED amount. We use probability as a
        # weight to estimate how much will actually fall in the root zone.
        # Effective fraction capped at 80% (runoff/evaporation losses).
        prob_fraction = min(rain_probability_24h / 100.0, 1.0)
        effective_rain = min(forecast_precipitation_24h * prob_fraction * 0.8, depletion)
        effective_rain = max(0.0, round(effective_rain, 2))

        # Net irrigation requirement (mm): depletion minus what rain will cover plus daily crop demand
        # Subject to minimum = 0
        net_irrigation = max(0.0, round(depletion + etc - effective_rain, 1))
        # Gross irrigation (accounting for application efficiency)
        gross_irrigation = max(0.0, round(net_irrigation / eff, 1)) if net_irrigation > 0 else 0.0
        # L/ha: 1mm over 1 hectare = 10,000 L
        litres_per_hectare = int(round(gross_irrigation * 10_000))

        # ── Decision Logic ────────────────────────────────────────────────────
        # Priority 1: Over-saturation / recent heavy rain
        if soil_moisture >= (fc * 1.02) or recent_rainfall_mm >= 30.0:
            action = "REDUCE IRRIGATION"
            reason = (
                f"Soil moisture ({soil_moisture:.1f}%) is at or above field capacity ({fc:.1f}%). "
                f"Excess water causes root hypoxia. Stop all irrigation."
            )
            priority = "high"
            decision_confidence = "HIGH"
            gross_irrigation = 0.0
            litres_per_hectare = 0

        # Priority 2: Imminent significant rain — postpone if soil is above wilting point
        elif forecast_precipitation_24h >= 8.0 and rain_probability_24h >= 65.0 and soil_moisture > wp:
            action = "WAIT"
            reason = (
                f"Rain expected: Forecast {forecast_precipitation_24h:.1f} mm rain ({rain_probability_24h:.0f}% probability). "
                f"Current soil moisture ({soil_moisture:.1f}%) is above wilting point ({wp:.1f}%). "
                f"Postpone irrigation to avoid waterlogging and nutrient runoff."
            )
            priority = "low"
            decision_confidence = "MEDIUM"
            gross_irrigation = 0.0
            litres_per_hectare = 0

        # Priority 3: Critical depletion — soil is thirsty regardless of rain forecast
        elif depletion > raw and effective_rain < (depletion * 0.5):
            action = "IRRIGATE"
            reason = (
                f"Root-zone depletion ({depletion:.1f} mm) exceeds readily available water ({raw:.1f} mm). "
                f"Estimated crop demand today: {etc:.1f} mm (ET₀={et0:.1f} mm × Kc={kc}). "
                f"Expected effective rainfall ({effective_rain:.1f} mm) is insufficient to cover deficit."
            )
            priority = "urgent" if (soil_moisture <= wp or depletion > (taw * 0.75)) else "high"
            decision_confidence = "HIGH"

        # Priority 4: Depletion manageable AND moderate rain expected
        elif depletion <= raw and forecast_precipitation_24h >= 4.0 and rain_probability_24h >= 50.0:
            action = "WAIT"
            reason = (
                f"Rain expected: Forecast {forecast_precipitation_24h:.1f} mm rain at {rain_probability_24h:.0f}% probability. "
                f"Soil moisture ({soil_moisture:.1f}%) is within safe range (depletion={depletion:.1f} mm ≤ RAW={raw:.1f} mm). "
                f"Expected rain should cover today's crop demand ({etc:.1f} mm)."
            )
            priority = "low"
            decision_confidence = "MEDIUM"
            gross_irrigation = 0.0
            litres_per_hectare = 0

        # Priority 5: Borderline depletion with moderate ET₀
        elif depletion > 0 and depletion <= raw:
            action = "MONITOR"
            reason = (
                f"Soil moisture ({soil_moisture:.1f}%) is acceptable. "
                f"Depletion ({depletion:.1f} mm) is within readily available water limit ({raw:.1f} mm). "
                f"Today's estimated crop demand: {etc:.1f} mm. Continue monitoring."
            )
            priority = "low"
            decision_confidence = "HIGH"
            gross_irrigation = 0.0
            litres_per_hectare = 0

        # Priority 6: Soil is at or above optimal
        else:
            action = "MONITOR"
            reason = (
                f"Soil moisture ({soil_moisture:.1f}%) is near field capacity. "
                f"No irrigation required at this time."
            )
            priority = "low"
            decision_confidence = "HIGH"
            gross_irrigation = 0.0
            litres_per_hectare = 0

        # Application method
        if action == "IRRIGATE":
            recommended_method = "drip" if s_type in ["sandy", "loamy"] else "micro-sprinkler"
        else:
            recommended_method = "none"

        return {
            "action": action,
            # Renamed: this is NOT ML confidence — it is decision quality score
            "decision_confidence": decision_confidence,
            # Keep 'confidence' key for backward-compat with existing frontend
            "confidence": {"HIGH": 0.90, "MEDIUM": 0.70, "LOW": 0.50}.get(decision_confidence, 0.75),
            "reason": reason,
            "priority": priority,
            "water_amount_mm": gross_irrigation,
            "litres_per_hectare": litres_per_hectare,
            "recommended_method": recommended_method,
            "soil_moisture_level": soil_moisture,
            "field_capacity_reference": fc,
            "crop_coefficient_kc": kc,
            # Transparent water-balance breakdown
            "water_balance": {
                "field_capacity_pct":   fc,
                "wilting_point_pct":    wp,
                "root_zone_depth_mm":   rzd,
                "taw_mm":               round(taw, 1),
                "raw_mm":               round(raw, 1),
                "depletion_mm":         round(depletion, 1),
                "et0_mm":               round(et0, 2),
                "et0_source":           "open_meteo" if (et0_mm and et0_mm > 0) else "estimated",
                "kc":                   kc,
                "etc_mm":               etc,
                "forecast_rain_mm":     forecast_precipitation_24h,
                "rain_probability_pct": rain_probability_24h,
                "effective_rain_mm":    effective_rain,
                "net_irrigation_mm":    net_irrigation,
                "gross_irrigation_mm":  gross_irrigation,
                "application_efficiency": eff,
            },
            "disclaimer": (
                "This irrigation recommendation is based on an agronomic water-balance model. "
                "Real-world application should account for actual field soil-moisture sensors, "
                "local weather observations, and agronomist advice. "
                "ET₀ values sourced from Open-Meteo FAO-56 Penman-Monteith estimates."
            ),
        }


precision_irrigation_engine = PrecisionIrrigationEngine()


def get_disease_recommendations(disease_class_key: str, is_healthy: bool = False) -> Dict[str, Any]:
    """Retrieve disease treatments, preventions, pesticides, and organic remedies."""
    if is_healthy:
        return DISEASE_DATABASE.get("Healthy")

    disease_name = disease_class_key.replace("___", "_").split("_", 1)[-1]
    for key, value in DISEASE_DATABASE.items():
        if key.lower() in disease_name.lower():
            return value

    return {
        "treatments": [
            "Prune infected foliage and isolate the plant cluster",
            "Submit leaf sample to local agriculture extension agent",
            "Monitor adjacent rows for symptom progression",
        ],
        "prevention": [
            "Maintain adequate spacing for canopy aeration",
            "Sanitize pruning instruments between rows",
            "Avoid overhead irrigation during evening hours",
        ],
        "pesticides": ["Consult an agronomic specialist for appropriate chemical class rotation"],
        "organic": ["Apply certified organic copper or horticultural neem oil"],
    }


def get_crop_from_class(disease_class_key: str) -> str:
    """Extract clean crop name from disease class key."""
    parts = disease_class_key.split("___")
    if parts:
        prefix = parts[0].replace("(", "").replace(")", "").split()[0].lower()
        for key, val in CROP_MAPPING.items():
            if key in prefix:
                return val
    return "Crop"
