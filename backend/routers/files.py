"""
CropPulse – Files Router
Streams assets (images, PDFs) directly from MongoDB GridFS bucket.
Provides clean public access for frontend display and downloads.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import io
from loguru import logger
from backend.services.gridfs_service import gridfs_service

router = APIRouter()

@router.get("/{file_id}")
async def get_file(file_id: str):
    """
    Download/Stream a file stored in GridFS by ID.
    Supports streaming large media items and PDFs.
    """
    try:
        content, filename, content_type = await gridfs_service.download_file(file_id)
        
        # Stream response directly from bytes
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "public, max-age=31536000"
            }
        )
    except Exception as e:
        logger.warning(f"File not found or failed to stream: {file_id}. Error: {e}")
        raise HTTPException(
            status_code=404,
            detail="Requested file not found in storage."
        )
