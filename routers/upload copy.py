# from fastapi import APIRouter, UploadFile, File, HTTPException
# from typing import List
# import cloudinary.uploader

# router = APIRouter(prefix="/upload", tags=["Upload"])


# @router.post("/product-images")
# async def upload_product_images(
#     # CHANGED: Made optional with default=[]
#     files: List[UploadFile] = File(default=[])
# ):
#     """
#     Upload multiple product images (0-5 images allowed)
#     Returns list of Cloudinary URLs
#     """
#     # ADDED: Handle empty list (no images)
#     if len(files) == 0:
#         return {
#             "success": True,
#             "image_urls": [],
#             "public_ids": [],
#             "count": 0
#         }

#     if len(files) > 5:
#         raise HTTPException(
#             status_code=400,
#             detail="Maximum 5 images allowed"
#         )

#     # REMOVED: Minimum image requirement check
#     # if len(files) < 1:
#     #     raise HTTPException(
#     #         status_code=400,
#     #         detail="At least 1 image is required"
#     #     )

#     uploaded_urls = []
#     uploaded_public_ids = []

#     try:
#         for file in files:
#             # Validate file type
#             if not file.content_type.startswith('image/'):
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"File {file.filename} must be an image"
#                 )

#             # Upload to Cloudinary
#             result = cloudinary.uploader.upload(
#                 file.file,
#                 folder="products",
#                 resource_type="image",
#                 allowed_formats=["jpg", "png", "jpeg", "webp"],
#                 transformation=[
#                     {'width': 1000, 'height': 1000, 'crop': 'limit'},
#                     {'quality': 'auto'},
#                     {'fetch_format': 'auto'}
#                 ]
#             )

#             uploaded_urls.append(result['secure_url'])
#             uploaded_public_ids.append(result['public_id'])

#         return {
#             "success": True,
#             "image_urls": uploaded_urls,
#             "public_ids": uploaded_public_ids,
#             "count": len(uploaded_urls)
#         }

#     except Exception as e:
#         # Cleanup uploaded images if error occurs
#         for public_id in uploaded_public_ids:
#             try:
#                 cloudinary.uploader.destroy(public_id)
#             except:
#                 pass

#         raise HTTPException(
#             status_code=500,
#             detail=f"Upload failed: {str(e)}"
#         )


# @router.delete("/product-image")
# async def delete_product_image(public_id: str):
#     """
#     Delete single image from Cloudinary
#     public_id example: "products/abc123"
#     """
#     try:
#         result = cloudinary.uploader.destroy(public_id)

#         if result['result'] == 'ok':
#             return {
#                 "success": True,
#                 "message": "Image deleted successfully"
#             }
#         else:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Image not found"
#             )

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Delete failed: {str(e)}"
#         )
