from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

# ❌ GALAT LINE (Delete this)
# from app.database import database

# ✅ SAHI LINE (Import get_db directly)
from app.database import get_db

from app import models, schemas

router = APIRouter()


# ✅ Update Dependency Here (database.get_db -> get_db)
@router.get("/featured", response_model=List[schemas.ProductReviewResponse])
async def get_featured_reviews(db: AsyncSession = Depends(get_db)):
    """Fetch featured reviews for the home page"""

    # ... baaki code same rahega ...
    query = select(models.ProductReview).where(
        models.ProductReview.is_featured == True
    ).options(
        selectinload(models.ProductReview.user)
    ).limit(3)

    result = await db.execute(query)
    reviews = result.scalars().all()

    formatted_reviews = []
    for review in reviews:
        formatted_reviews.append(schemas.ProductReviewResponse(
            id=review.id,
            product_id=review.product_id,
            user_id=review.user_id,
            user_name=review.user.full_name if review.user else "Anonymous",
            user_avatar=None,
            rating=review.rating,
            comment=review.comment,
            is_verified_purchase=review.is_verified_purchase,
            helpful_count=review.helpful_count,
            created_at=str(review.created_at),
            updated_at=str(review.updated_at),
            image_urls=[],
            is_approved=review.is_approved,
            is_featured=review.is_featured
        ))

    return formatted_reviews