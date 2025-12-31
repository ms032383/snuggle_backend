from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import cloudinary.uploader
from .. import models, schemas, database, dependencies

router = APIRouter()


# ==========================================
# 1. GET ALL ADD-ONS (For "Complete the Surprise")
# ==========================================
@router.get("/add-ons", response_model=List[schemas.ProductResponse])
async def get_add_on_products(db: AsyncSession = Depends(database.get_db)):
    """Fetch products marked as Add-ons from the main Product table"""
    result = await db.execute(
        select(models.Product)
        .where(models.Product.is_active == True, models.Product.is_addon == True)
        .limit(10)
    )
    return result.scalars().all()


# 2. CREATE ADD-ON (Admin Only)
@router.post("/add-ons", response_model=schemas.AddOnProductResponse)
async def create_add_on(
        name: str = Form(...),
        price: float = Form(...),
        category: str = Form("General"),
        image: UploadFile = File(...),
        db: AsyncSession = Depends(database.get_db),
        # current_user: models.User = Depends(dependencies.get_current_admin) # Uncomment for security
):
    # Upload Image
    upload_result = cloudinary.uploader.upload(image.file, folder="snuggle_addons")
    image_url = upload_result.get("secure_url")

    new_addon = models.AddOnProduct(
        name=name,
        price=price,
        category=category,
        image_url=image_url,
        is_active=True
    )
    db.add(new_addon)
    await db.commit()
    await db.refresh(new_addon)
    return new_addon


# 3. DELETE ADD-ON (Admin Only)
@router.delete("/add-ons/{id}")
async def delete_add_on(
        id: int,
        db: AsyncSession = Depends(database.get_db),
        # current_user: models.User = Depends(dependencies.get_current_admin)
):
    result = await db.execute(select(models.AddOnProduct).where(models.AddOnProduct.id == id))
    addon = result.scalar_one_or_none()

    if not addon:
        raise HTTPException(status_code=404, detail="Add-on not found")

    await db.delete(addon)
    await db.commit()
    return {"message": "Add-on deleted successfully"}


# ==========================================
# 2. TOGGLE ADD-ON STATUS (For Admin Panel)
# ==========================================
@router.patch("/products/{product_id}/toggle-addon")
async def toggle_addon_status(
        product_id: int,
        db: AsyncSession = Depends(database.get_db),
        # current_user: models.User = Depends(dependencies.get_current_admin) # Uncomment for security
):
    """Mark/Unmark a product as an Add-on"""

    # 1. Product dhoondo
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Status Toggle karo (True <-> False)
    # Note: Ensure 'is_addon' column exists in 'products' table via models.py
    if product.is_addon is None:
        product.is_addon = True
    else:
        product.is_addon = not product.is_addon

    await db.commit()
    await db.refresh(product)

    status_msg = "added to" if product.is_addon else "removed from"
    return {"message": f"Product {status_msg} Add-ons list", "is_addon": product.is_addon}