from fastapi import APIRouter, Depends, HTTPException, Query
from requests import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json
from datetime import datetime
from .. import models, schemas, database, dependencies
from app.schemas import ProductDetailResponse, ProductUpdateExtended
from ..database import get_db
from ..models import Product, ProductColor, ProductSpecification, ProductImage
router = APIRouter()


# --- CATEGORY API ---
@router.post("/categories", response_model=schemas.CategoryResponse)
async def create_category(
        category: schemas.CategoryCreate,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Create a new category (Admin only)"""
    new_cat = models.Category(**category.dict())
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)
    return new_cat


@router.get("/categories", response_model=List[schemas.CategoryResponse])
async def get_categories(db: AsyncSession = Depends(database.get_db)):
    """Get all categories"""
    result = await db.execute(select(models.Category))
    return result.scalars().all()


# --- ENHANCED PRODUCT API ---

# 1. Create Product with Extended Features
@router.post("/", response_model=schemas.ProductDetailResponse)
async def create_product_extended(
        product: schemas.ProductCreateExtended,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Create product with extended features (Admin only)"""
    # Check if category exists
    cat_result = await db.execute(
        select(models.Category).where(models.Category.id == product.category_id)
    )
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Category ID not found")

    # Create main product
    product_data = product.dict()

    # Remove nested data for main product creation
    gallery_images = product_data.pop('gallery_images', [])
    colors = product_data.pop('colors', [])
    specifications = product_data.pop('specifications', [])

    # Set default MRP if not provided
    if not product_data.get('mrp'):
        product_data['mrp'] = product_data['price'] * 1.5  # 50% markup

    # Set SKU if not provided
    if not product_data.get('sku'):
        product_data['sku'] = f"SKU-{int(datetime.now().timestamp())}"

    new_product = models.Product(**product_data)
    db.add(new_product)
    await db.flush()  # Get the product ID without committing

    # Add gallery images
    for i, image_url in enumerate(gallery_images):
        gallery_image = models.ProductImage(
            product_id=new_product.id,
            image_url=image_url,
            is_primary=(i == 0),
            display_order=i
        )
        db.add(gallery_image)

    # Add colors
    for color_data in colors:
        color = models.ProductColor(
            product_id=new_product.id,
            color_name=color_data['color_name'],
            color_code=color_data['color_code'],
            image_url=color_data.get('image_url'),
            is_available=color_data.get('is_available', True)
        )
        db.add(color)

    # Add specifications
    for i, spec_data in enumerate(specifications):
        spec = models.ProductSpecification(
            product_id=new_product.id,
            key=spec_data['key'],
            value=spec_data['value'],
            display_order=i
        )
        db.add(spec)

    await db.commit()
    await db.refresh(new_product)

    # Return full product details
    return await get_product_full_details(new_product.id, db)


# 2. Get All Products with Enhanced Filtering
@router.get("/", response_model=List[schemas.ProductResponse])
async def get_products(
        db: AsyncSession = Depends(database.get_db),
        q: Optional[str] = None,  # Search Query
        category_id: Optional[int] = None,  # Filter by Category
        min_price: Optional[float] = None,  # Price Filter
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,  # Rating Filter
        in_stock: Optional[bool] = None,  # Stock Filter
        sort: Optional[str] = None,  # Sorting
        skip: int = 0,  # Pagination
        limit: int = 20  # Items per page
):
    """Get all products with enhanced filtering"""
    # Base Query
    query = select(models.Product).where(models.Product.is_active == True)

    # Apply Filters
    if q:
        query = query.where(
            models.Product.name.ilike(f"%{q}%") |
            models.Product.description.ilike(f"%{q}%") |
            models.Product.tags.ilike(f"%{q}%")
        )

    if category_id:
        query = query.where(models.Product.category_id == category_id)

    if min_price is not None:
        query = query.where(models.Product.price >= min_price)

    if max_price is not None:
        query = query.where(models.Product.price <= max_price)

    if min_rating is not None:
        query = query.where(models.Product.average_rating >= min_rating)

    if in_stock is not None:
        if in_stock:
            query = query.where(models.Product.stock > 0)
        else:
            query = query.where(models.Product.stock == 0)

    # Apply Sorting
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

    # Apply Pagination
    query = query.offset(skip).limit(limit)

    # Execute
    result = await db.execute(query)
    return result.scalars().all()


# 3. Get Single Product with Full Details
@router.get("/{id}", response_model=schemas.ProductDetailResponse)
async def get_product_detail(id: int, db: AsyncSession = Depends(database.get_db)):
    """Get single product with all related data"""
    return await get_product_full_details(id, db)


# 4. Update Product with Extended Fields
@router.put("/{product_id}", response_model=schemas.ProductDetailResponse)  # ✅ Fixed URL & Added @
async def update_product(  # ✅ Added async
        product_id: int,
        payload: schemas.ProductUpdateExtended,  # ✅ Correct Schema
        db: AsyncSession = Depends(database.get_db),  # ✅ Async Session
        current_user: models.User = Depends(dependencies.get_current_admin)  # ✅ Added Auth
):
    # 1. Fetch Product
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    data = payload.dict(exclude_unset=True)

    # 2. Update Basic Fields
    for field in ["name", "description", "price", "mrp", "stock", "image_url", "sku", "tags", "is_active",
                  "category_id"]:
        if field in data:
            setattr(product, field, data[field])

    # 3. Update Gallery Images (Delete Old -> Add New)
    if "gallery_images" in data:
        # Delete old images
        await db.execute(
            select(models.ProductImage).where(models.ProductImage.product_id == product.id)
        )
        # Note: SQLAlchemy async delete logic varies, simpler is to clear list if relationship allows,
        # but explicit delete is safer.
        # Actually simplest async way for relationships:
        product.gallery_images = []  # Clear logic handled by ORM if cascade is set, else manual delete

        # Add new images
        for idx, url in enumerate(data["gallery_images"]):
            # Create new object
            new_img = models.ProductImage(
                image_url=url,
                is_primary=(idx == 0),
                display_order=idx
            )
            product.gallery_images.append(new_img)

    # 4. Update Colors
    if "colors" in data:
        product.colors = []  # Clear old
        for c in data["colors"]:
            # c is a dict from Pydantic model
            new_color = models.ProductColor(
                color_name=c['color_name'],
                color_code=c['color_code'],
                image_url=c.get('image_url'),
                is_available=c.get('is_available', True)
            )
            product.colors.append(new_color)

    # 5. Update Specifications
    if "specifications" in data:
        product.specifications = []  # Clear old
        for s in data["specifications"]:
            new_spec = models.ProductSpecification(
                key=s['key'],
                value=s['value'],
                display_order=s.get('display_order', 0)
            )
            product.specifications.append(new_spec)

    await db.commit()
    await db.refresh(product)

    # Return full details
    return await get_product_full_details(product_id, db)

# 5. Delete Product
@router.delete("/{product_id}")
async def delete_product(
        product_id: int,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Delete a product (Admin only) - Soft delete by setting is_active=False"""
    query = select(models.Product).where(models.Product.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Soft delete
    product.is_active = False
    await db.commit()

    return {"message": f"Product {product.name} has been deactivated"}


# 6. Get Product Reviews
@router.post("/{product_id}/reviews", response_model=schemas.ProductReviewResponse)
async def submit_review(
        product_id: int,
        review: schemas.ReviewCreate,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    """
    Allow logged-in customer to review a product AND update product rating.
    """
    # 1. Check if product exists
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Check if user already reviewed
    existing_review = await db.execute(
        select(models.ProductReview)
        .where(models.ProductReview.user_id == current_user.id, models.ProductReview.product_id == product_id)
    )
    if existing_review.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already reviewed this product")

    # 3. Create Review
    new_review = models.ProductReview(
        product_id=product_id,
        user_id=current_user.id,
        rating=review.rating,
        comment=review.comment,
        is_approved=False,  # Admin approval required? (Set True if auto-approve)
        is_featured=False,
        helpful_count=0,
        is_verified_purchase=False,
        created_at=str(datetime.now()),
        updated_at=str(datetime.now())
    )
    db.add(new_review)

    # ✅ 4. UPDATE PRODUCT RATING (Calculations)
    current_count = product.review_count or 0
    current_avg = product.average_rating or 0.0

    # Calculate New Average
    # Formula: (Old_Total_Score + New_Rating) / New_Count
    new_count = current_count + 1
    total_score = (current_count * current_avg) + review.rating
    new_average = total_score / new_count

    # Update Product Fields
    product.review_count = new_count
    product.average_rating = round(new_average, 1)  # 1 decimal place (e.g., 4.5)

    db.add(product)  # Mark product as updated

    # 5. Commit Transaction
    await db.commit()
    await db.refresh(new_review)

    # Return Response
    return {
        "id": new_review.id,
        "product_id": new_review.product_id,
        "user_id": new_review.user_id,
        "user_name": current_user.full_name or "Guest",
        "rating": new_review.rating,
        "comment": new_review.comment,
        "is_verified_purchase": new_review.is_verified_purchase,
        "helpful_count": new_review.helpful_count,
        "created_at": str(new_review.created_at),
        "updated_at": str(new_review.updated_at),
        "image_urls": [],
        "is_approved": new_review.is_approved,
        "is_featured": new_review.is_featured
    }

# 7. Add Product Review
@router.get("/{product_id}/full", response_model=schemas.ProductDetailResponse)
async def get_product_full_details(
        product_id: int,
        db: AsyncSession = Depends(database.get_db)
):
    """Get product with all related data (Safe Mode)"""

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

    # 👇 LOGIC: Calculate Rating & Count Dynamically
    real_reviews = product.reviews or []
    real_count = len(real_reviews)

    if real_count > 0:
        # Handle case where rating might be None in DB
        total_stars = sum((r.rating or 0) for r in real_reviews)
        real_rating = round(total_stars / real_count, 1)
    else:
        real_rating = 0.0

    # Format reviews (With Safety Try-Catch)
    formatted_reviews = []
    for review in real_reviews:
        # ✅ CRASH FIX: Safe JSON Parsing
        review_images = []
        if review.image_urls:
            try:
                review_images = json.loads(review.image_urls)
            except Exception:
                review_images = []  # Ignore bad data

        formatted_reviews.append(schemas.ProductReviewResponse(
            id=review.id,
            product_id=review.product_id,
            user_id=review.user_id,
            user_name=review.user.full_name if (review.user and review.user.full_name) else "Anonymous",
            user_avatar=None,
            rating=review.rating or 0,
            comment=review.comment or "",
            is_verified_purchase=review.is_verified_purchase,
            helpful_count=review.helpful_count,
            created_at=str(review.created_at),
            updated_at=str(review.updated_at),
            image_urls=review_images,
            is_approved=review.is_approved,
            is_featured=review.is_featured
        ))

    # Safe Gallery Extraction
    gallery = []
    if product.gallery_images:
        gallery = [img.image_url for img in product.gallery_images if img.image_url]

    # Create response
    return schemas.ProductDetailResponse(
        id=product.id,
        name=product.name,
        description=product.description or "",
        price=product.price,
        mrp=product.mrp,
        stock=product.stock,
        image_url=product.image_url or "",
        category_id=product.category_id,
        is_active=product.is_active,
        sku=product.sku or "",

        tags=product.tags or [],

        average_rating=real_rating,
        review_count=real_count,

        wishlist_count=product.wishlist_count,
        gallery_images=gallery,
        colors=[{"color_name": c.color_name, "color_code": c.color_code, "image_url": c.image_url} for c in
                (product.colors or [])],
        specifications=[{"key": s.key, "value": s.value} for s in (product.specifications or [])],
        reviews=formatted_reviews
    )
# 8. Get Recommended Products
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
        models.Product.is_active == True,
        models.Product.stock > 0
    ).order_by(
        models.Product.average_rating.desc(),  # Sort by rating
        models.Product.wishlist_count.desc(),  # Then by popularity
        models.Product.id.desc()  # Then by newest
    ).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


# 9. Get Product Images
@router.get("/{product_id}/images", response_model=List[schemas.ProductImageResponse])
async def get_product_images(
        product_id: int,
        db: AsyncSession = Depends(database.get_db)
):
    """Get all images for a product"""
    query = select(models.ProductImage).where(
        models.ProductImage.product_id == product_id
    ).order_by(models.ProductImage.display_order)

    result = await db.execute(query)
    return result.scalars().all()


# 10. Get Product Colors
@router.get("/{product_id}/colors", response_model=List[schemas.ProductColorResponse])
async def get_product_colors(
        product_id: int,
        db: AsyncSession = Depends(database.get_db)
):
    """Get all colors for a product"""
    query = select(models.ProductColor).where(
        models.ProductColor.product_id == product_id,
        models.ProductColor.is_available == True
    )

    result = await db.execute(query)
    return result.scalars().all()


# 11. Mark Review as Helpful
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


# 12. Get Add-on Products
@router.get("/add-ons")
async def get_add_on_products(db: AsyncSession = Depends(database.get_db)):
    """Get suggested add-on products for cart"""
    result = await db.execute(
        select(models.Product)
        .where(models.Product.stock > 0, models.Product.is_active == True)
        .order_by(models.Product.id.desc())
        .limit(4)
    )
    products = result.scalars().all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "image_url": p.image_url,
            "price": p.price,
            "category": "addon"
        }
        for p in products
    ]


# 13. Bulk Update Products (Admin only)
@router.patch("/bulk/update")
async def bulk_update_products(
        bulk_data: schemas.BulkProductUpdate,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Bulk update multiple products (Admin only)"""
    if not bulk_data.product_ids:
        raise HTTPException(status_code=400, detail="No product IDs provided")

    update_data = bulk_data.dict(exclude_unset=True, exclude={"product_ids"})

    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    # Get products
    query = select(models.Product).where(models.Product.id.in_(bulk_data.product_ids))
    result = await db.execute(query)
    products = result.scalars().all()

    if not products:
        raise HTTPException(status_code=404, detail="No products found")

    # Update products
    for product in products:
        for field, value in update_data.items():
            if value is not None:
                setattr(product, field, value)

    await db.commit()

    return {"message": f"Updated {len(products)} products successfully"}


# Helper function to get full product details
async def get_product_full_details(product_id: int, db: AsyncSession):
    """Get product with all related data"""
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
        image_urls = json.loads(review.image_urls) if review.image_urls else []
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
            image_urls=image_urls
        ))

    # Create response
    return schemas.ProductDetailResponse(
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

        # ✅ FIX: Handle None (null) value from DB
        tags=product.tags or [],

        average_rating=product.average_rating,
        review_count=product.review_count,
        wishlist_count=product.wishlist_count,
        gallery_images=[img.image_url for img in product.gallery_images],
        colors=[{"color_name": c.color_name, "color_code": c.color_code, "image_url": c.image_url} for c in
                product.colors],
        specifications=[{"key": s.key, "value": s.value} for s in product.specifications],
        reviews=formatted_reviews
    )