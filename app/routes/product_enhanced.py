from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json
from datetime import datetime
from .. import models, schemas, database, dependencies

router = APIRouter()


# 1. GET PRODUCT WITH ALL DETAILS
@router.get("/{product_id}/full", response_model=schemas.ProductDetailResponse)
async def get_product_full_details(
        product_id: int,
        db: AsyncSession = Depends(database.get_db)
):
    """Get product with all related data (images, colors, reviews, etc.)"""

    # Query with all relationships
    query = select(models.Product).where(models.Product.id == product_id).options(
        selectinload(models.Product.gallery_images),
        selectinload(models.Product.colors),
        selectinload(models.Product.specifications),
        selectinload(models.Product.reviews).selectinload(models.ProductReview.user),
        selectinload(models.Product.category)
    )

    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Format reviews with user info
    formatted_reviews = []
    for review in product.reviews:
        formatted_reviews.append(schemas.ProductReviewResponse(
            id=review.id,
            product_id=review.product_id,
            user_id=review.user_id,
            user_name=review.user.full_name if review.user else "Anonymous",
            user_avatar=None,  # Add if you have user avatars
            rating=review.rating,
            comment=review.comment,
            is_verified_purchase=review.is_verified_purchase,
            helpful_count=review.helpful_count,
            created_at=review.created_at,
            updated_at=review.updated_at,
            image_urls=json.loads(review.image_urls) if review.image_urls else []
        ))

    # Create response
    response = schemas.ProductDetailResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        mrp=product.mrp,
        stock=product.stock,
        image_url=product.image_url,
        category_id=product.category_id,
        is_active=product.is_active,
        sku=product.sku,
        tags=product.tags,
        average_rating=product.average_rating,
        review_count=product.review_count,
        wishlist_count=product.wishlist_count,
        gallery_images=product.gallery_images,
        colors=product.colors,
        specifications=product.specifications,
        reviews=formatted_reviews
    )

    return response


# 2. ADD PRODUCT REVIEW
@router.post("/{product_id}/reviews", response_model=schemas.ProductReviewResponse)
async def add_product_review(
        product_id: int,
        review_data: schemas.ProductReviewCreate,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    """Add a review for a product"""

    # Check if product exists
    product_result = await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if user has already reviewed this product
    existing_review = await db.execute(
        select(models.ProductReview).where(
            models.ProductReview.product_id == product_id,
            models.ProductReview.user_id == current_user.id
        )
    )

    if existing_review.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already reviewed this product")

    # Create review
    new_review = models.ProductReview(
        product_id=product_id,
        user_id=current_user.id,
        rating=review_data.rating,
        comment=review_data.comment,
        is_verified_purchase=review_data.is_verified_purchase,
        image_urls=json.dumps(review_data.image_urls) if review_data.image_urls else None,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )

    # Update product rating
    total_reviews = product.review_count + 1
    total_rating = (product.average_rating * product.review_count) + review_data.rating
    new_average = total_rating / total_reviews

    product.average_rating = round(new_average, 1)
    product.review_count = total_reviews

    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)

    return new_review


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