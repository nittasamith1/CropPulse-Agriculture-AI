"""
CropPulse – Prediction Repository
Data access operations for plant disease and soil moisture predictions, history, and aggregations.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from backend.config import settings
from backend.repositories.base_repository import BaseRepository
from backend.database import db


class PredictionRepository:
    def __init__(self):
        self.disease_repo = BaseRepository(
            collection_name=settings.COLLECTION_DISEASE_PREDICTIONS,
            id_field="prediction_id",
        )
        self.soil_repo = BaseRepository(
            collection_name=settings.COLLECTION_SOIL_PREDICTIONS,
            id_field="prediction_id",
        )

    # ── Disease Predictions ───────────────────────────────────────────────────
    async def save_disease_prediction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.disease_repo.create(data["prediction_id"], data)

    async def get_disease_prediction(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        return await self.disease_repo.get(prediction_id)

    async def list_disease_predictions_paginated(
        self,
        user_id: Optional[str] = None,
        farm_id: Optional[str] = None,
        severity: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}
        if user_id:
            query["user_id"] = user_id
        if farm_id:
            query["farm_id"] = farm_id
        if severity:
            query["severity"] = severity

        return await self.disease_repo.list_paginated(
            filter_query=query, page=page, page_size=page_size, sort_by="created_at", descending=True
        )

    # ── Soil Predictions ──────────────────────────────────────────────────────
    async def save_soil_prediction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.soil_repo.create(data["prediction_id"], data)

    async def get_soil_prediction(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        return await self.soil_repo.get(prediction_id)

    async def list_soil_predictions_paginated(
        self,
        user_id: Optional[str] = None,
        farm_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}
        if user_id:
            query["user_id"] = user_id
        if farm_id:
            query["farm_id"] = farm_id

        return await self.soil_repo.list_paginated(
            filter_query=query, page=page, page_size=page_size, sort_by="created_at", descending=True
        )

    # ── Analytics Aggregations ────────────────────────────────────────────────
    async def get_analytics_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate total predictions, disease distribution, and average confidence."""
        match_stage = {"$match": {"user_id": user_id}} if user_id else {"$match": {}}

        # Total counts
        total_disease = await self.disease_repo.count(match_stage.get("$match", {}))
        total_soil = await self.soil_repo.count(match_stage.get("$match", {}))

        # Disease breakdown
        pipeline_disease = [
            match_stage,
            {"$group": {"_id": "$disease_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 6},
        ]
        breakdown = await self.disease_repo.aggregate(pipeline_disease)

        return {
            "total_disease_predictions": total_disease,
            "total_soil_predictions": total_soil,
            "total_predictions": total_disease + total_soil,
            "top_diseases": [{"disease": b["_id"], "count": b["count"]} for b in breakdown if b.get("_id")],
        }

    async def get_severity_breakdown(self, user_id: Optional[str] = None) -> Dict[str, int]:
        """Return counts by severity level: healthy, mild, moderate, severe, uncertain."""
        match_stage = {"$match": {"user_id": user_id}} if user_id else {"$match": {}}
        pipeline = [
            match_stage,
            {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
        ]
        results = await self.disease_repo.aggregate(pipeline)
        breakdown = {"healthy": 0, "mild": 0, "moderate": 0, "severe": 0, "uncertain": 0}
        for item in results:
            sev = (item.get("_id") or "").lower()
            if sev in breakdown:
                breakdown[sev] = item["count"]
            elif sev:
                breakdown[sev] = item["count"]
        return breakdown

    async def get_health_counts(self, user_id: Optional[str] = None) -> Dict[str, int]:
        """Return total healthy and diseased plant counts."""
        match_query = {"user_id": user_id} if user_id else {}
        healthy = await self.disease_repo.count({**match_query, "is_healthy": True})
        diseased = await self.disease_repo.count({**match_query, "is_healthy": False})
        return {"healthy_count": healthy, "diseased_count": diseased}

    async def get_soil_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Compute average soil moisture and count of plots requiring irrigation."""
        match_stage = {"$match": {"user_id": user_id}} if user_id else {"$match": {}}
        pipeline = [
            match_stage,
            {
                "$group": {
                    "_id": None,
                    "avg_moisture": {"$avg": "$predicted_moisture"},
                    "irrigation_needed": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$or": [
                                        {"$eq": ["$irrigation_recommended", True]},
                                        {"$eq": ["$irrigation_action", "IRRIGATE"]},
                                        {"$eq": ["$irrigation_action", "REDUCE_IRRIGATION"]},
                                    ]
                                },
                                1,
                                0,
                            ]
                        }
                    },
                }
            },
        ]
        results = await self.soil_repo.aggregate(pipeline)
        if results and results[0]:
            avg_m = results[0].get("avg_moisture")
            return {
                "average_soil_moisture": round(float(avg_m), 1) if avg_m is not None else 0.0,
                "irrigation_needed_count": int(results[0].get("irrigation_needed", 0)),
            }
        return {"average_soil_moisture": 0.0, "irrigation_needed_count": 0}

    async def get_monthly_counts(
        self, user_id: Optional[str] = None, months: int = 6
    ) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Return monthly prediction counts for disease and soil over the last N months."""
        from datetime import datetime, timezone
        import calendar

        now = datetime.now(timezone.utc)
        month_keys = []
        cur_year = now.year
        cur_month = now.month
        for _ in range(months):
            month_label = f"{calendar.month_abbr[cur_month]} {cur_year}"
            month_keys.append((cur_year, cur_month, month_label))
            cur_month -= 1
            if cur_month < 1:
                cur_month = 12
                cur_year -= 1

        disease_counts = {label: 0 for _, _, label in month_keys}
        soil_counts = {label: 0 for _, _, label in month_keys}

        oldest_year, oldest_month, _ = month_keys[-1]
        start_date = datetime(oldest_year, oldest_month, 1, tzinfo=timezone.utc)

        match_disease: Dict[str, Any] = {"created_at": {"$gte": start_date}}
        match_soil: Dict[str, Any] = {"created_at": {"$gte": start_date}}
        if user_id:
            match_disease["user_id"] = user_id
            match_soil["user_id"] = user_id

        pipeline_disease = [
            {"$match": match_disease},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"},
                    },
                    "count": {"$sum": 1},
                }
            },
        ]
        pipeline_soil = [
            {"$match": match_soil},
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"},
                    },
                    "count": {"$sum": 1},
                }
            },
        ]

        try:
            d_res = await self.disease_repo.aggregate(pipeline_disease)
            for item in d_res:
                y = item.get("_id", {}).get("year")
                m = item.get("_id", {}).get("month")
                if y and m and 1 <= m <= 12:
                    lbl = f"{calendar.month_abbr[m]} {y}"
                    if lbl in disease_counts:
                        disease_counts[lbl] = item["count"]
        except Exception:
            pass

        try:
            s_res = await self.soil_repo.aggregate(pipeline_soil)
            for item in s_res:
                y = item.get("_id", {}).get("year")
                m = item.get("_id", {}).get("month")
                if y and m and 1 <= m <= 12:
                    lbl = f"{calendar.month_abbr[m]} {y}"
                    if lbl in soil_counts:
                        soil_counts[lbl] = item["count"]
        except Exception:
            pass

        return disease_counts, soil_counts


prediction_repository = PredictionRepository()
