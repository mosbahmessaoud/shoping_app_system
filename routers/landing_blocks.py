# routers/landing_blocks.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from models.product import Product
from schemas.landing_blocks import LandingBlocksUpdate, LandingBlocksResponse
from utils.db import get_db
from utils.auth import get_current_admin

router = APIRouter(prefix="/product", tags=["Product Landing Blocks"])


@router.get("/{product_id}/landing-blocks", response_model=LandingBlocksResponse)
def get_landing_blocks(product_id: int, db: Session = Depends(get_db)):
    """
    Obtenir les blocs de la page de vente d'un produit (accès public,
    utilisé aussi par le storefront, donc pas d'authentification requise).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé"
        )

    blocks = []
    if product.landing_blocks:
        try:
            blocks = json.loads(product.landing_blocks)
        except (json.JSONDecodeError, TypeError):
            blocks = []

    return LandingBlocksResponse(product_id=product.id, blocks=blocks)


@router.put("/{product_id}/landing-blocks", response_model=LandingBlocksResponse)
def update_landing_blocks(
    product_id: int,
    update_data: LandingBlocksUpdate,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Mettre à jour les blocs de la page de vente d'un produit (admin seulement).
    Appelé depuis l'app Flutter. Les images doivent déjà être uploadées sur
    Cloudinary via /upload/product-images avant d'être référencées ici.

    Remplace entièrement la liste des blocs existants (pas de fusion partielle) -
    envoyez la liste complète à chaque mise à jour.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé"
        )

    product.landing_blocks = json.dumps(update_data.blocks, ensure_ascii=False)
    db.commit()
    db.refresh(product)

    return LandingBlocksResponse(product_id=product.id, blocks=update_data.blocks)


@router.delete("/{product_id}/landing-blocks", status_code=status.HTTP_204_NO_CONTENT)
def clear_landing_blocks(
    product_id: int,
    current_admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Effacer les blocs de la page de vente (revient à l'affichage de
    la description simple). Admin seulement.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé"
        )

    product.landing_blocks = None
    db.commit()
    return None
