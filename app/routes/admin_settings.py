from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import cloudinary.uploader
from .. import models, schemas, database, dependencies
from datetime import datetime

router = APIRouter()


# Helper to get or create store business settings
async def get_or_create_business_settings(db: AsyncSession) -> models.StoreSettings:
    """Get the single business settings row, or create it if missing"""
    result = await db.execute(select(models.StoreSettings))
    settings = result.scalars().first()

    if not settings:
        settings = models.StoreSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return settings


# GET store business settings
@router.get("/settings", response_model=schemas.StoreSettingsResponse)
async def get_store_business_settings(
        current_user: models.User = Depends(dependencies.get_current_admin),
        db: AsyncSession = Depends(database.get_db)
):
    """Get store business details (name, address, GST, etc.) - Admin only"""
    settings = await get_or_create_business_settings(db)
    return settings


# UPDATE store business settings
@router.put("/settings", response_model=schemas.StoreSettingsResponse)
async def update_store_business_settings(
        settings_data: schemas.StoreSettingsCreate,
        current_user: models.User = Depends(dependencies.get_current_admin),
        db: AsyncSession = Depends(database.get_db)
):
    """Update store business details - Admin only"""
    result = await db.execute(select(models.StoreSettings))
    settings = result.scalars().first()

    if not settings:
        settings = models.StoreSettings(**settings_data.dict())
        db.add(settings)
    else:
        for field, value in settings_data.dict().items():
            if value is not None:
                setattr(settings, field, value)
        settings.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(settings)
    return settings


# Simple form-based update (if needed)
@router.post("/settings/update-form")
async def update_store_settings_form(
        store_name: str = Form(...),
        address: str = Form(...),
        phone: str = Form(...),
        email: str = Form(...),
        gstin: str = Form(...),
        current_user: models.User = Depends(dependencies.get_current_admin),
        db: AsyncSession = Depends(database.get_db)
):
    """Update store settings via form data"""
    result = await db.execute(select(models.StoreSettings))
    settings = result.scalars().first()

    if not settings:
        settings = models.StoreSettings(
            store_name=store_name,
            address=address,
            phone=phone,
            email=email,
            gstin=gstin
        )
        db.add(settings)
    else:
        settings.store_name = store_name
        settings.address = address
        settings.phone = phone
        settings.email = email
        settings.gstin = gstin
        settings.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(settings)

    return {
        "message": "Store settings updated successfully",
        "data": {
            "id": settings.id,
            "store_name": settings.store_name,
            "address": settings.address,
            "phone": settings.phone,
            "email": settings.email,
            "gstin": settings.gstin,
            "updated_at": str(settings.updated_at)
        }
    }