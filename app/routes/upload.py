from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import cloudinary
import cloudinary.uploader

router = APIRouter()

# =========================================================
# 1. DIRECT CONFIGURATION (Hardcoded for Fix)
# =========================================================

cloudinary.config(
    cloud_name="dvoxhfgrt",
    api_key="672468764517841",
    api_secret="TTyqUEDmXc1T5X89nVMQKySKTfg",  # ✅ Aapki Secret Key yahan hai
    secure=True
)


# =========================================================
# 2. UPLOAD API ROUTES
# =========================================================

@router.post("/multiple", summary="Upload Multiple Images")
async def upload_multiple_images(images: List[UploadFile] = File(...)):
    uploaded_urls = []

    print("--- Starting Upload Process ---")

    for image in images:
        try:
            print(f"📤 Uploading: {image.filename}...")

            # Direct Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                image.file,
                folder="snuggle_products",
                resource_type="auto"
            )

            url = upload_result.get("secure_url")
            print(f"✅ Success! URL: {url}")
            uploaded_urls.append(url)

        except Exception as e:
            print(f"❌ Upload Failed for {image.filename}: {e}")
            continue

    if not uploaded_urls:
        print("🔴 All uploads failed.")
        raise HTTPException(status_code=500, detail="Failed to upload images. Check server console.")

    return {"urls": uploaded_urls}


@router.post("/", summary="Upload Single Image")
async def upload_image(file: UploadFile = File(...)):
    try:
        print(f"📤 Uploading Single: {file.filename}...")
        res = cloudinary.uploader.upload(file.file, folder="snuggle_uploads", resource_type="auto")
        print(f"✅ Success: {res.get('secure_url')}")
        return {"url": res.get("secure_url")}
    except Exception as e:
        print(f"❌ Single Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))