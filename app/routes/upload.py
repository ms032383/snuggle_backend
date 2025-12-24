from fastapi import APIRouter, UploadFile, File, HTTPException
import cloudinary
import cloudinary.uploader
import os

router = APIRouter()

# 1. Configuration (Apni Keys yahan daalein)
# Production mein ye .env file se aana chahiye
cloudinary.config(
    cloud_name="dvoxhfgrt",
    api_key="672468764517841",
    api_secret="TTyqUEDmXc1T5X89nVMQKySKTfg"
)


# 2. UPLOAD IMAGE API
@router.post("/", summary="Upload Image to Cloudinary")
async def upload_image(file: UploadFile = File(...)):
    """
    Ye endpoint file accept karega aur Cloudinary URL return karega.
    """
    try:
        # File ko Cloudinary par upload karo
        upload_result = cloudinary.uploader.upload(file.file)

        # Wahan se URL nikalo
        url = upload_result.get("secure_url")

        return {
            "url": url,
            "message": "Image uploaded successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")