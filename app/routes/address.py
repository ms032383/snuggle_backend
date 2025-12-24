from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from .. import models, schemas, database, dependencies

router = APIRouter()


# 1. ADD NEW ADDRESS
@router.post("/", response_model=schemas.AddressResponse)
async def create_address(
        address: schemas.AddressCreate,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    new_address = models.Address(**address.dict(), user_id=current_user.id)
    db.add(new_address)
    await db.commit()
    await db.refresh(new_address)
    return new_address


# 2. GET ALL SAVED ADDRESSES
@router.get("/", response_model=List[schemas.AddressResponse])
async def get_addresses(
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.Address).where(models.Address.user_id == current_user.id))
    return result.scalars().all()


# 3. DELETE ADDRESS (Optional but useful)
@router.delete("/{id}")
async def delete_address(
        id: int,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(
        select(models.Address).where(models.Address.id == id, models.Address.user_id == current_user.id))
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(status_code=404, detail="Address not found")

    await db.delete(address)
    await db.commit()
    return {"message": "Address deleted"}