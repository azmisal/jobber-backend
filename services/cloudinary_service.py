import cloudinary
import cloudinary.uploader
from config.settings import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

def upload_pdf(file_bytes: bytes, filename: str) -> str:
    """Uploads document byte data directly to Cloudinary storage buckets."""
    response = cloudinary.uploader.upload(
        file_bytes,
        resource_type="raw",
        public_id=f"resumes/{filename}.pdf",
        invalidate=True
    )
    return response.get("secure_url")