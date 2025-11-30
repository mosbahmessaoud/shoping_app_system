from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from models.category import Category
from models.product import Product
from schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryWithCount
from utils.db import get_db
from utils.auth import get_current_admin

router = APIRouter(prefix="/category", tags=["Category"])

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Créer une nouvelle catégorie (admin seulement)"""
    
    # Vérifier si la catégorie existe déjà
    existing_category = db.query(Category).filter(Category.name == category_data.name).first()
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette catégorie existe déjà"
        )
    
    new_category = Category(**category_data.dict())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return new_category

@router.get("/", response_model=List[CategoryWithCount])
def get_all_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Obtenir toutes les catégories avec le nombre de produits"""
    
    categories = db.query(
        Category,
        func.count(Product.id).label('product_count')
    ).outerjoin(Product).group_by(Category.id).offset(skip).limit(limit).all()
    
    result = []
    for category, product_count in categories:
        result.append(CategoryWithCount(
            id=category.id,
            name=category.name,
            description=category.description,
            created_at=category.created_at,
            product_count=product_count
        ))
    
    return result

@router.get("/{category_id}", response_model=CategoryResponse)
def get_category_by_id(
    category_id: int,
    db: Session = Depends(get_db)
):
    """Obtenir une catégorie par son ID"""
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catégorie non trouvée"
        )
    
    return category

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Mettre à jour une catégorie (admin seulement)"""
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catégorie non trouvée"
        )
    
    # Vérifier si le nouveau nom existe déjà
    if category_data.name and category_data.name != category.name:
        existing = db.query(Category).filter(Category.name == category_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom de catégorie existe déjà"
            )
        category.name = category_data.name
    
    if category_data.description is not None:
        category.description = category_data.description
    
    db.commit()
    db.refresh(category)
    
    return category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Supprimer une catégorie (admin seulement)"""
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catégorie non trouvée"
        )
    
    # Vérifier s'il y a des produits dans cette catégorie
    product_count = db.query(Product).filter(Product.category_id == category_id).count()
    if product_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de supprimer cette catégorie car elle contient {product_count} produit(s)"
        )
    
    db.delete(category)
    db.commit()
    
    return None