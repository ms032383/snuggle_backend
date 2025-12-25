from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from .. import models, schemas, database, dependencies

router = APIRouter()

# --- CATEGORY API ---
@router.post("/categories", response_model=schemas.CategoryResponse)
async def create_category(category: schemas.CategoryCreate, db: AsyncSession = Depends(database.get_db)):
    new_cat = models.Category(**category.dict())
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)
    return new_cat

@router.get("/categories", response_model=List[schemas.CategoryResponse])
async def get_categories(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Category))
    return result.scalars().all()

# --- PRODUCT API ---

# 1. Create Product
@router.post("/", response_model=schemas.ProductResponse)
async def create_product(product: schemas.ProductCreate, db: AsyncSession = Depends(database.get_db)):
    # Check if category exists
    cat_result = await db.execute(select(models.Category).where(models.Category.id == product.category_id))
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Category ID not found")

    new_product = models.Product(**product.dict())
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return new_product

# 2. Get All Products (With Search, Filter & Pagination) 🔥
@router.get("/", response_model=List[schemas.ProductResponse])
async def get_products(
    db: AsyncSession = Depends(database.get_db),
    q: Optional[str] = None,          # Search Query (?q=teddy)
    category_id: Optional[int] = None, # Filter by Category
    min_price: Optional[float] = None, # Price Filter
    max_price: Optional[float] = None,
    sort: Optional[str] = None,       # Sort: low_to_high, high_to_low
    skip: int = 0,                    # Pagination (Offset)
    limit: int = 10                   # Pagination (Limit)
):
    # Base Query
    query = select(models.Product).where(models.Product.is_active == True)

    # Apply Filters
    if q:
        query = query.where(models.Product.name.ilike(f"%{q}%")) # Case insensitive search
    if category_id:
        query = query.where(models.Product.category_id == category_id)
    if min_price:
        query = query.where(models.Product.price >= min_price)
    if max_price:
        query = query.where(models.Product.price <= max_price)

    # Apply Sorting
    if sort == "low_to_high":
        query = query.order_by(models.Product.price.asc())
    elif sort == "high_to_low":
        query = query.order_by(models.Product.price.desc())
    else:
        query = query.order_by(models.Product.id.desc()) # Default: Newest first

    # Apply Pagination
    query = query.offset(skip).limit(limit)

    # Execute
    result = await db.execute(query)
    return result.scalars().all()

# 3. Get Single Product
@router.get("/{id}", response_model=schemas.ProductResponse)
async def get_product_detail(id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Product).where(models.Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
        product_id: int,
        product_data: schemas.ProductCreate,  # Using Create schema as it has all fields
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(dependencies.get_current_admin)  # Security: Only Admins
):
    # 1. Find Product
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Update Fields
    product.name = product_data.name
    product.description = product_data.description
    product.price = product_data.price
    product.stock = product_data.stock
    product.category_id = product_data.category_id

    # Update Image if provided (Upload logic frontend se URL bhejega)
    if product_data.image_url:
        product.image_url = product_data.image_url

    # 3. Save
    await db.commit()
    await db.refresh(product)

    return product


# ADD TO YOUR EXISTING PRODUCTS.PY

@router.get("/add-ons")
async def get_add_on_products(
        db: AsyncSession = Depends(database.get_db)
):
    """
    Get suggested add-on products for cart
    """
    result = await db.execute(
        select(models.Product)
        .where(models.Product.category_id == 9)  # Add-on category
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