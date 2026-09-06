"""
CropPulse – File Storage Service Abstraction
Provides pluggable object storage (GridFS default; ready for AWS S3, Cloudflare R2, or Azure Blob).
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from loguru import logger
from backend.services.gridfs_service import gridfs_service


class BaseStorageService(ABC):
    """Abstract interface for file storage backends."""

    @abstractmethod
    async def upload_file(self, content: bytes, filename: str, content_type: str, metadata: dict) -> str:
        """Upload file and return accessible URL / path."""
        pass

    @abstractmethod
    async def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """Download file content and content_type."""
        pass

    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Delete file by ID."""
        pass


class GridFSStorageService(BaseStorageService):
    """MongoDB GridFS storage implementation."""

    async def upload_file(self, content: bytes, filename: str, content_type: str, metadata: dict) -> str:
        user_id = metadata.get("user_id", "system")
        category = metadata.get("category", "leaf")

        if category == "report":
            return await gridfs_service.upload_report_pdf(content, filename, user_id)
        else:
            return await gridfs_service.upload_leaf_image(content, filename, user_id, content_type)

    async def download_file(self, file_id: str) -> Tuple[bytes, str]:
        return await gridfs_service.download_file(file_id)

    async def delete_file(self, file_id: str) -> bool:
        return await gridfs_service.delete_file(file_id)


# Primary storage provider (GridFS)
file_service: BaseStorageService = GridFSStorageService()
