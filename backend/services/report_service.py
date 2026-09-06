"""
CropPulse – Report Generation Service
Generates PDF and CSV reports of predictions and analytics.
"""

import asyncio
from datetime import datetime
from io import BytesIO, StringIO
import csv
from typing import Optional, List, Dict, Any
from loguru import logger

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from backend.config import settings
from backend.services.mongodb_service import MongoDBService
from backend.services.gridfs_service import gridfs_service
from backend.utils.helpers import generate_id, utc_now

_report_svc = MongoDBService(settings.COLLECTION_REPORTS, id_field="report_id")
_disease_svc = MongoDBService(settings.COLLECTION_DISEASE_PREDICTIONS, id_field="prediction_id")
_soil_svc = MongoDBService(settings.COLLECTION_SOIL_PREDICTIONS, id_field="prediction_id")


class ReportService:
    """Generates and manages PDF/CSV reports asynchronously."""

    async def generate_disease_report(
        self,
        user_id: str,
        user_name: str,
        prediction_ids: Optional[List[str]] = None,
        farm_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a PDF report of disease predictions.
        Loads predictions, generates PDF, uploads to GridFS, saves report metadata.
        """
        try:
            report_id = generate_id("report")
            now = utc_now()

            # Retrieve predictions
            if prediction_ids:
                predictions = []
                for pred_id in prediction_ids:
                    pred = await _disease_svc.get(pred_id)
                    if pred:
                        predictions.append(pred)
            else:
                # Retrieve recent predictions for user/farm
                if farm_id:
                    predictions = await _disease_svc.query("farm_id", "==", farm_id, order_by="created_at", limit=100)
                else:
                    predictions = await _disease_svc.query("user_id", "==", user_id, order_by="created_at", limit=100)

            if not predictions:
                raise ValueError("No predictions found to generate a report.")

            # Generate PDF bytes
            pdf_bytes = await asyncio.to_thread(self._create_disease_pdf, predictions, user_name)

            # Upload to GridFS
            filename = f"disease_report_{report_id}.pdf"
            pdf_url = await gridfs_service.upload_report_pdf(pdf_bytes, filename, user_id)

            # Save report record
            report_doc = {
                "report_id": report_id,
                "user_id": user_id,
                "report_type": "disease",
                "title": f"Disease Detection Report - {now.strftime('%Y-%m-%d')}",
                "pdf_url": pdf_url,
                "prediction_count": len(predictions),
                "created_at": now,
            }

            await _report_svc.create(report_id, report_doc)
            logger.info(f"✅ Disease report generated: {report_id}")
            return report_doc

        except Exception as e:
            logger.error(f"Failed to generate disease report: {e}")
            raise e

    async def generate_soil_report(
        self,
        user_id: str,
        user_name: str,
        prediction_ids: Optional[List[str]] = None,
        farm_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a PDF report of soil predictions.
        Loads predictions, generates PDF, uploads to GridFS, saves report metadata.
        """
        try:
            report_id = generate_id("report")
            now = utc_now()

            # Retrieve predictions
            if prediction_ids:
                predictions = []
                for pred_id in prediction_ids:
                    pred = await _soil_svc.get(pred_id)
                    if pred:
                        predictions.append(pred)
            else:
                # Retrieve recent predictions for user/farm
                if farm_id:
                    predictions = await _soil_svc.query("farm_id", "==", farm_id, order_by="created_at", limit=100)
                else:
                    predictions = await _soil_svc.query("user_id", "==", user_id, order_by="created_at", limit=100)

            if not predictions:
                raise ValueError("No predictions found to generate a report.")

            # Generate PDF bytes
            pdf_bytes = await asyncio.to_thread(self._create_soil_pdf, predictions, user_name)

            # Upload to GridFS
            filename = f"soil_report_{report_id}.pdf"
            pdf_url = await gridfs_service.upload_report_pdf(pdf_bytes, filename, user_id)

            # Save report record
            report_doc = {
                "report_id": report_id,
                "user_id": user_id,
                "report_type": "soil",
                "title": f"Soil Moisture Report - {now.strftime('%Y-%m-%d')}",
                "pdf_url": pdf_url,
                "prediction_count": len(predictions),
                "created_at": now,
            }

            await _report_svc.create(report_id, report_doc)
            logger.info(f"✅ Soil report generated: {report_id}")
            return report_doc

        except Exception as e:
            logger.error(f"Failed to generate soil report: {e}")
            raise e

    async def generate_combined_report(
        self,
        user_id: str,
        user_name: str,
        farm_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a PDF report of combined predictions (disease + soil).
        Loads predictions, generates PDF, uploads to GridFS, saves report metadata.
        """
        try:
            report_id = generate_id("report")
            now = utc_now()

            # Retrieve predictions
            if farm_id:
                d_preds = await _disease_svc.query("farm_id", "==", farm_id, order_by="created_at", limit=50)
                s_preds = await _soil_svc.query("farm_id", "==", farm_id, order_by="created_at", limit=50)
            else:
                d_preds = await _disease_svc.query("user_id", "==", user_id, order_by="created_at", limit=50)
                s_preds = await _soil_svc.query("user_id", "==", user_id, order_by="created_at", limit=50)

            if not d_preds and not s_preds:
                raise ValueError("No predictions found to generate a report.")

            # Generate PDF bytes
            pdf_bytes = await asyncio.to_thread(self._create_combined_pdf, d_preds, s_preds, user_name)

            # Upload to GridFS
            filename = f"combined_report_{report_id}.pdf"
            pdf_url = await gridfs_service.upload_report_pdf(pdf_bytes, filename, user_id)

            # Save report record
            report_doc = {
                "report_id": report_id,
                "user_id": user_id,
                "report_type": "combined",
                "title": f"Combined Health Report - {now.strftime('%Y-%m-%d')}",
                "pdf_url": pdf_url,
                "prediction_count": len(d_preds) + len(s_preds),
                "created_at": now,
            }

            await _report_svc.create(report_id, report_doc)
            logger.info(f"✅ Combined report generated: {report_id}")
            return report_doc

        except Exception as e:
            logger.error(f"Failed to generate combined report: {e}")
            raise e

    async def generate_csv_report(
        self,
        user_id: str,
        report_type: str,
        farm_id: Optional[str] = None
    ) -> str:
        """
        Generates CSV report contents.
        Returns CSV data string.
        """
        output = StringIO()
        writer = csv.writer(output)

        if report_type == "disease":
            writer.writerow(["Date", "Prediction ID", "Crop Type", "Disease Name", "Confidence", "Severity", "Latitude", "Longitude"])
            if farm_id:
                preds = await _disease_svc.query("farm_id", "==", farm_id, limit=500)
            else:
                preds = await _disease_svc.query("user_id", "==", user_id, limit=500)
            
            for p in preds:
                writer.writerow([
                    str(p.get("created_at", ""))[:19],
                    p.get("prediction_id"),
                    p.get("crop_type"),
                    p.get("disease_name"),
                    f"{p.get('confidence', 0):.2%}",
                    p.get("severity"),
                    p.get("latitude"),
                    p.get("longitude")
                ])

        elif report_type == "soil":
            writer.writerow(["Date", "Prediction ID", "Predicted Moisture (%)", "Irrigation Recommended", "Water Req (mm)", "Irrigation Type", "Latitude", "Longitude"])
            if farm_id:
                preds = await _soil_svc.query("farm_id", "==", farm_id, limit=500)
            else:
                preds = await _soil_svc.query("user_id", "==", user_id, limit=500)
            
            for p in preds:
                writer.writerow([
                    str(p.get("created_at", ""))[:19],
                    p.get("prediction_id"),
                    f"{p.get('predicted_moisture', 0):.1f}%",
                    p.get("irrigation_recommended"),
                    p.get("water_requirement_mm"),
                    p.get("irrigation_type"),
                    p.get("latitude"),
                    p.get("longitude")
                ])

        return output.getvalue()

    def _create_disease_pdf(self, predictions: List[Dict], user_name: str) -> bytes:
        """Create a disease prediction PDF document."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#2E7D32"),
            spaceAfter=20,
            alignment=1,  # Center
        )
        story.append(Paragraph("🌾 CropPulse Disease Report", title_style))
        story.append(Spacer(1, 0.2 * inch))

        # Metadata
        meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#555555"))
        story.append(Paragraph(f"<b>Farmer:</b> {user_name}", meta_style))
        story.append(Paragraph(f"<b>Generated On:</b> {utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}", meta_style))
        story.append(Paragraph(f"<b>Total Predictions Analyzed:</b> {len(predictions)}", meta_style))
        story.append(Spacer(1, 0.3 * inch))

        # Table data
        table_data = [
            ["Date", "Crop", "Disease Detected", "Confidence", "Severity"]
        ]

        for pred in predictions:
            created = pred.get("created_at", "")
            date_str = str(created)[:10] if created else "N/A"
            table_data.append([
                date_str,
                pred.get("crop_type", "N/A"),
                pred.get("disease_name", "N/A"),
                f"{pred.get('confidence', 0):.1%}",
                pred.get("severity", "N/A"),
            ])

        table = Table(table_data, colWidths=[1.2*inch, 1.2*inch, 2.2*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F1F8E9"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8E6C9")),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
        ]))
        story.append(table)

        doc.build(story)
        return buffer.getvalue()

    def _create_soil_pdf(self, predictions: List[Dict], user_name: str) -> bytes:
        """Create a soil prediction PDF document."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1976D2"),
            spaceAfter=20,
            alignment=1,  # Center
        )
        story.append(Paragraph("💧 CropPulse Soil Moisture Report", title_style))
        story.append(Spacer(1, 0.2 * inch))

        meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#555555"))
        story.append(Paragraph(f"<b>Farmer:</b> {user_name}", meta_style))
        story.append(Paragraph(f"<b>Generated On:</b> {utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}", meta_style))
        story.append(Paragraph(f"<b>Total Predictions Analyzed:</b> {len(predictions)}", meta_style))
        story.append(Spacer(1, 0.3 * inch))

        table_data = [
            ["Date", "Soil Type", "Moisture Level", "Irrigation Recommended", "Water Req (mm)"]
        ]

        for pred in predictions:
            created = pred.get("created_at", "")
            date_str = str(created)[:10] if created else "N/A"
            inputs = pred.get("input_features", {})
            soil_type = inputs.get("soil_type", pred.get("soil_type", "N/A"))
            
            table_data.append([
                date_str,
                soil_type.capitalize(),
                f"{pred.get('predicted_moisture', 0):.1f}%",
                "Yes" if pred.get("irrigation_recommended") else "No",
                f"{pred.get('water_requirement_mm', 0):.1f} mm"
            ])

        table = Table(table_data, colWidths=[1.2*inch, 1.2*inch, 1.5*inch, 1.8*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#E3F2FD"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBDEFB")),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
        ]))
        story.append(table)

        doc.build(story)
        return buffer.getvalue()

    def _create_combined_pdf(self, d_preds: List[Dict], s_preds: List[Dict], user_name: str) -> bytes:
        """Create a combined health PDF document."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#2E7D32"),
            spaceAfter=20,
            alignment=1,  # Center
        )
        story.append(Paragraph("🌿 CropPulse Combined Health Report", title_style))
        story.append(Spacer(1, 0.2 * inch))

        meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#555555"))
        story.append(Paragraph(f"<b>Farmer:</b> {user_name}", meta_style))
        story.append(Paragraph(f"<b>Generated On:</b> {utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}", meta_style))
        story.append(Spacer(1, 0.2 * inch))

        # Section 1: Diseases
        section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#2E7D32"), spaceBefore=10, spaceAfter=10)
        story.append(Paragraph("Disease Analysis History", section_style))

        if d_preds:
            d_table_data = [["Date", "Crop", "Disease Detected", "Confidence", "Severity"]]
            for p in d_preds:
                c = p.get("created_at", "")
                d_table_data.append([
                    str(c)[:10] if c else "N/A",
                    p.get("crop_type", "N/A"),
                    p.get("disease_name", "N/A"),
                    f"{p.get('confidence', 0):.1%}",
                    p.get("severity", "N/A")
                ])
            table = Table(d_table_data, colWidths=[1.2*inch, 1.2*inch, 2.2*inch, 1.2*inch, 1.2*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8E6C9")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F1F8E9"), colors.white]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No disease prediction logs found.", styles["Normal"]))

        story.append(Spacer(1, 0.3 * inch))

        # Section 2: Soil Moisture
        story.append(Paragraph("Soil Moisture History", section_style))

        if s_preds:
            s_table_data = [["Date", "Soil Type", "Moisture Level", "Irrigation Recommended", "Water Req (mm)"]]
            for p in s_preds:
                c = p.get("created_at", "")
                inputs = p.get("input_features", {})
                soil_type = inputs.get("soil_type", p.get("soil_type", "N/A"))
                s_table_data.append([
                    str(c)[:10] if c else "N/A",
                    soil_type.capitalize(),
                    f"{p.get('predicted_moisture', 0):.1f}%",
                    "Yes" if p.get("irrigation_recommended") else "No",
                    f"{p.get('water_requirement_mm', 0):.1f} mm"
                ])
            table = Table(s_table_data, colWidths=[1.2*inch, 1.2*inch, 1.5*inch, 1.8*inch, 1.3*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976D2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBDEFB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#E3F2FD"), colors.white]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No soil prediction logs found.", styles["Normal"]))

        doc.build(story)
        return buffer.getvalue()

    async def get_user_reports(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch reports generated by a user."""
        try:
            return await _report_svc.query("user_id", "==", user_id, order_by="created_at", descending=True, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get reports for {user_id}: {e}")
            return []

    async def get_report(self, report_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific report ensuring proper user ownership."""
        try:
            report = await _report_svc.get(report_id)
            if report and report.get("user_id") == user_id:
                return report
            return None
        except Exception as e:
            logger.error(f"Failed to get report {report_id}: {e}")
            return None


# Singleton instance
report_service = ReportService()
