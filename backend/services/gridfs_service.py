"""
CropPulse – GridFS Storage Service
Handles storage of leaf images, PDFs, and general assets in MongoDB GridFS.
"""

import uuid
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from loguru import logger
from backend.database import db
from backend.config import settings

class GridFSService:
    """Manages file storage using MongoDB GridFS bucket."""

    @property
    def bucket(self) -> AsyncIOMotorGridFSBucket:
        """Return the active GridFS bucket."""
        return db.gridfs_bucket

    async def upload_file(
        self,
        content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        metadata: dict = None
    ) -> str:
        """
        Upload binary content to GridFS.
        Returns a URL to fetch the file.
        """
        try:
            if not metadata:
                metadata = {}
            
            metadata["content_type"] = content_type
            
            # Write to GridFS
            file_id = await self.bucket.upload_from_stream(
                filename,
                content,
                metadata=metadata
            )
            file_id_str = str(file_id)
            logger.info(f"✅ GridFS uploaded file: {filename} (id={file_id_str})")
            
            # Generate local URL serving through the files router
            # We assume a host relative or configurable base URL
            api_base = settings.FRONTEND_URL  # or backend URL, but since frontend requests it, we direct to backend
            url = f"/api/v1/files/{file_id_str}"
            return url
        except Exception as e:
            logger.error(f"GridFS upload failed: {e}")
            raise e

    async def upload_leaf_image(
        self,
        content: bytes,
        filename: str,
        user_id: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """Upload leaf image to GridFS and return file URL."""
        metadata = {
            "user_id": user_id,
            "file_type": "leaf_image"
        }
        return await self.upload_file(
            content=content,
            filename=filename,
            content_type=content_type,
            metadata=metadata
        )

    async def upload_report_pdf(
        self,
        content: bytes,
        filename: str,
        user_id: str,
    ) -> str:
        """Upload PDF report to GridFS and return file URL."""
        metadata = {
            "user_id": user_id,
            "file_type": "report_pdf"
        }
        return await self.upload_file(
            content=content,
            filename=filename,
            content_type="application/pdf",
            metadata=metadata
        )

    async def download_file(self, file_id_str: str) -> tuple[bytes, str, str]:
        """
        Download a file from GridFS.
        Returns (content, filename, content_type).
        """
        from bson import ObjectId
        try:
            file_id = ObjectId(file_id_str)
            # Retrieve file stream
            grid_out = await self.bucket.open_download_stream(file_id)
            content = await grid_out.read()
            filename = grid_out.filename
            
            # Extract content type
            meta = grid_out.metadata or {}
            content_type = meta.get("content_type", "application/octet-stream")
            
            return content, filename, content_type
        except Exception as e:
            logger.error(f"GridFS download failed for id={file_id_str}: {e}")
            raise e

    async def delete_file(self, file_id_str: str) -> bool:
        """Delete a file from GridFS."""
        from bson import ObjectId
        try:
            file_id = ObjectId(file_id_str)
            await self.bucket.delete(file_id)
            logger.info(f"✅ GridFS file deleted: {file_id_str}")
            return True
        except Exception as e:
            logger.error(f"GridFS file deletion failed for id={file_id_str}: {e}")
            return False

# Singleton instance
gridfs_service = GridFSService()
