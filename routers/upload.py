from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import cloudinary.uploader
import logging

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/product-images")
async def upload_product_images(
    files: List[UploadFile] = File(default=[])
):
    """
    Upload multiple product images (0-5 images allowed)
    Returns list of Cloudinary URLs

    IMPORTANT: Set Content-Type as multipart/form-data in your client
    """
    try:
        # Handle empty list (no images)
        if not files or len(files) == 0:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "image_urls": [],
                    "public_ids": [],
                    "count": 0,
                    "message": "No images uploaded"
                }
            )

        # Validate number of files
        if len(files) > 5:
            raise HTTPException(
                status_code=400,
                detail="Maximum 5 images allowed"
            )

        uploaded_urls = []
        uploaded_public_ids = []

        for idx, file in enumerate(files):
            # Check if file is actually provided
            if not file or not file.filename:
                logger.warning(f"Empty file at index {idx}, skipping...")
                continue

            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{file.filename}' must be an image (received: {file.content_type})"
                )

            # Read file content
            try:
                file_content = await file.read()

                # Check if file is empty
                if len(file_content) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File '{file.filename}' is empty"
                    )

                # Reset file pointer for Cloudinary
                await file.seek(0)

            except Exception as read_error:
                logger.error(
                    f"Error reading file {file.filename}: {str(read_error)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot read file '{file.filename}': {str(read_error)}"
                )

            # Upload to Cloudinary
            try:
                result = cloudinary.uploader.upload(
                    file.file,
                    folder="products",
                    resource_type="image",
                    allowed_formats=["jpg", "png", "jpeg", "webp", "gif"],
                    transformation=[
                        {'width': 1000, 'height': 1000, 'crop': 'limit'},
                        {'quality': 'auto'},
                        {'fetch_format': 'auto'}
                    ]
                )

                uploaded_urls.append(result['secure_url'])
                uploaded_public_ids.append(result['public_id'])

                logger.info(
                    f"Successfully uploaded {file.filename} to Cloudinary")

            except Exception as upload_error:
                logger.error(
                    f"Cloudinary upload failed for {file.filename}: {str(upload_error)}")

                # Cleanup already uploaded images
                for public_id in uploaded_public_ids:
                    try:
                        cloudinary.uploader.destroy(public_id)
                        logger.info(f"Cleaned up {public_id}")
                    except Exception as cleanup_error:
                        logger.error(
                            f"Cleanup failed for {public_id}: {str(cleanup_error)}")

                raise HTTPException(
                    status_code=500,
                    detail=f"Cloudinary upload failed for '{file.filename}': {str(upload_error)}"
                )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "image_urls": uploaded_urls,
                "public_ids": uploaded_public_ids,
                "count": len(uploaded_urls),
                "message": f"Successfully uploaded {len(uploaded_urls)} image(s)"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.delete("/product-image")
async def delete_product_image(public_id: str):
    """
    Delete single image from Cloudinary

    Parameters:
    - public_id: Cloudinary public_id (e.g., "products/abc123")
    """
    if not public_id:
        raise HTTPException(
            status_code=400,
            detail="public_id is required"
        )

    try:
        result = cloudinary.uploader.destroy(public_id)

        if result.get('result') == 'ok':
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Image '{public_id}' deleted successfully"
                }
            )
        elif result.get('result') == 'not found':
            raise HTTPException(
                status_code=404,
                detail=f"Image '{public_id}' not found"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Delete failed with result: {result.get('result')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed for {public_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Delete failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Check if Cloudinary is configured correctly
    """
    try:
        import cloudinary
        config = cloudinary.config()

        return {
            "status": "healthy",
            "cloudinary_configured": bool(config.cloud_name and config.api_key and config.api_secret),
            "cloud_name": config.cloud_name if config.cloud_name else "NOT_SET"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
