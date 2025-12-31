from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json
from datetime import datetime

from .products import get_product_full_details
from .. import models, schemas, database, dependencies

router = APIRouter()


# 1. GET PRODUCT WITH ALL DETAILS
# 1. GET PRODUCT WITH ALL DETAILS
@router.get("/{product_id}/full", response_model=schemas.ProductDetailResponse)
async def get_product_full_details_route(
        product_id: int,
        db: AsyncSession = Depends(database.get_db)
):
    """Get product with all related data - Calls the helper function"""
    # Direct niche wala fixed helper function call karo
    return await get_product_full_details(product_id, db)

# 2. ADD PRODUCT REVIEW
@router.get("/{product_id}/reviews", response_model=List[schemas.ProductReviewResponse])
async def get_product_reviews(
        product_id: int,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "recent",  # recent, rating_high, rating_low
        db: AsyncSession = Depends(database.get_db)
):
    """Fetch reviews for a product with pagination and sorting"""

    # 1. Start Query
    query = select(models.ProductReview).where(models.ProductReview.product_id == product_id)

    # 2. Load User Relationship (Zaruri hai username ke liye)
    query = query.options(selectinload(models.ProductReview.user))

    # 3. Apply Sorting
    if sort_by == "recent":
        query = query.order_by(models.ProductReview.created_at.desc())
    elif sort_by == "rating_high":
        query = query.order_by(models.ProductReview.rating.desc())
    elif sort_by == "rating_low":
        query = query.order_by(models.ProductReview.rating.asc())

    # 4. Apply Pagination
    query = query.offset(skip).limit(limit)

    # 5. Execute Query
    result = await db.execute(query)
    reviews = result.scalars().all()

    # 6. Format Response
    formatted_reviews = []
    for review in reviews:
        # Handle Image URLs (JSON string to List)
        image_urls = []
        if review.image_urls:
            try:
                image_urls = json.loads(review.image_urls)
            except:
                image_urls = []

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
            image_urls=image_urls,

            # ✅ IMPORTANT FIX: These fields were missing causing 500 Error
            is_approved=review.is_approved,
            is_featured=review.is_featured
        ))

    return formatted_reviews


# 3. GET RECOMMENDED PRODUCTS
@router.get("/{product_id}/recommended", response_model=List[schemas.ProductResponse])
async def get_recommended_products(
        product_id: int,
        limit: int = Query(4, ge=1, le=20),
        db: AsyncSession = Depends(database.get_db)
):
    """Get recommended products based on category and popularity"""

    # Get current product category
    product_result = await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )
    current_product = product_result.scalar_one_or_none()

    if not current_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get products from same category (excluding current product)
    query = select(models.Product).where(
        models.Product.category_id == current_product.category_id,
        models.Product.id != product_id,
        models.Product.is_active == True
    ).order_by(
        models.Product.average_rating.desc(),  # Sort by rating
        models.Product.wishlist_count.desc()  # Then by popularity
    ).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


# 4. GET PRODUCT REVIEWS WITH PAGINATION
@router.get("/{product_id}/reviews", response_model=List[schemas.ProductReviewResponse])
async def get_product_reviews(
        product_id: int,
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=50),
        sort_by: str = Query("recent", regex="^(recent|helpful|rating)$"),
        db: AsyncSession = Depends(database.get_db)
):
    """Get product reviews with sorting and pagination"""

    # Base query
    query = select(models.ProductReview).where(
        models.ProductReview.product_id == product_id
    ).options(selectinload(models.ProductReview.user))

    # Apply sorting
    if sort_by == "helpful":
        query = query.order_by(models.ProductReview.helpful_count.desc())
    elif sort_by == "rating":
        query = query.order_by(models.ProductReview.rating.desc())
    else:  # recent
        query = query.order_by(models.ProductReview.created_at.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    reviews = result.scalars().all()

    # Format response
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
            created_at=review.created_at,
            updated_at=review.updated_at,
            image_urls=json.loads(review.image_urls) if review.image_urls else []
        ))

    return formatted_reviews


# 5. MARK REVIEW AS HELPFUL
@router.post("/reviews/{review_id}/helpful")
async def mark_review_helpful(
        review_id: int,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    """Mark a review as helpful"""

    # Get review
    review_result = await db.execute(
        select(models.ProductReview).where(models.ProductReview.id == review_id)
    )
    review = review_result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Increment helpful count
    review.helpful_count += 1
    await db.commit()

    return {"message": "Marked as helpful", "helpful_count": review.helpful_count}


# 6. GET PRODUCTS BY MULTIPLE FILTERS
@router.get("/", response_model=List[schemas.ProductResponse])
async def get_products_enhanced(
        db: AsyncSession = Depends(database.get_db),
        q: Optional[str] = None,
        category_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        in_stock: Optional[bool] = None,
        sort: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
):
    """Get products with enhanced filtering"""

    query = select(models.Product).where(models.Product.is_active == True)

    # Apply filters
    if q:
        query = query.where(models.Product.name.ilike(f"%{q}%"))

    if category_id:
        query = query.where(models.Product.category_id == category_id)

    if min_price:
        query = query.where(models.Product.price >= min_price)

    if max_price:
        query = query.where(models.Product.price <= max_price)

    if min_rating:
        query = query.where(models.Product.average_rating >= min_rating)

    if in_stock:
        query = query.where(models.Product.stock > 0)

    # Apply sorting
    if sort == "price_asc":
        query = query.order_by(models.Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(models.Product.price.desc())
    elif sort == "rating":
        query = query.order_by(models.Product.average_rating.desc())
    elif sort == "popular":
        query = query.order_by(models.Product.wishlist_count.desc())
    elif sort == "newest":
        query = query.order_by(models.Product.id.desc())
    else:
        query = query.order_by(models.Product.id.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()