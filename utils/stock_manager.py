from sqlalchemy.orm import Session
from models.product import Product
from models.stock_alert import StockAlert
from utils.notification_manager import create_stock_alert_notification

def check_and_create_stock_alert(db: Session, product: Product) -> StockAlert:
    """
    Vérifier le niveau de stock d'un produit et créer une alerte si nécessaire
    
    Args:
        db: Session de base de données
        product: Produit à vérifier
        
    Returns:
        StockAlert si une alerte a été créée, sinon None
    """
    
    # Vérifier s'il existe déjà une alerte non résolue pour ce produit
    existing_alert = db.query(StockAlert).filter(
        StockAlert.product_id == product.id,
        StockAlert.is_resolved == False
    ).first()
    
    # Si le stock est critique (0 ou inférieur)
    if product.quantity_in_stock <= 0:
        if not existing_alert or existing_alert.alert_type != "out_of_stock":
            # Résoudre l'ancienne alerte si elle existe
            if existing_alert:
                existing_alert.is_resolved = True
            
            # Créer une nouvelle alerte critique
            alert = StockAlert(
                product_id=product.id,
                alert_type="out_of_stock",
                message=f"CRITIQUE: Le produit '{product.name}' est en rupture de stock (0 unités restantes)"
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            # Créer une notification pour l'admin
            create_stock_alert_notification(db, alert, product)
            
            return alert
    
    # Si le stock est faible (inférieur ou égal au minimum)
    elif product.quantity_in_stock <= product.minimum_stock_level:
        if not existing_alert or existing_alert.alert_type != "low_stock":
            # Résoudre l'ancienne alerte si elle existe
            if existing_alert:
                existing_alert.is_resolved = True
            
            # Créer une nouvelle alerte de stock faible
            alert = StockAlert(
                product_id=product.id,
                alert_type="low_stock",
                message=f"ATTENTION: Le produit '{product.name}' a un stock faible ({product.quantity_in_stock} unités restantes, minimum recommandé: {product.minimum_stock_level})"
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            # Créer une notification pour l'admin
            create_stock_alert_notification(db, alert, product)
            
            return alert
    
    # Si le stock est suffisant, résoudre les alertes existantes
    elif existing_alert:
        from datetime import datetime
        existing_alert.is_resolved = True
        existing_alert.resolved_at = datetime.now()
        db.commit()
    
    return None

def check_product_availability(db: Session, product_id: int, quantity: int) -> dict:
    """
    Vérifier si un produit est disponible en quantité suffisante
    
    Args:
        db: Session de base de données
        product_id: ID du produit
        quantity: Quantité demandée
        
    Returns:
        dict avec 'available' (bool) et 'message' (str)
    """
    
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        return {
            "available": False,
            "message": f"Produit avec ID {product_id} non trouvé"
        }
    
    if not product.is_active:
        return {
            "available": False,
            "message": f"Le produit '{product.name}' n'est pas disponible"
        }
    
    if product.quantity_in_stock < quantity:
        return {
            "available": False,
            "message": f"Stock insuffisant pour '{product.name}'. Stock disponible: {product.quantity_in_stock}, demandé: {quantity}"
        }
    
    return {
        "available": True,
        "message": f"Le produit '{product.name}' est disponible",
        "product": product
    }

def update_product_stock(db: Session, product_id: int, quantity_change: int, operation: str = "decrease") -> Product:
    """
    Mettre à jour le stock d'un produit
    
    Args:
        db: Session de base de données
        product_id: ID du produit
        quantity_change: Quantité à ajouter ou retirer
        operation: "increase" pour ajouter, "decrease" pour retirer
        
    Returns:
        Product mis à jour
    """
    
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise ValueError(f"Produit avec ID {product_id} non trouvé")
    
    if operation == "increase":
        product.quantity_in_stock += quantity_change
    elif operation == "decrease":
        if product.quantity_in_stock < quantity_change:
            raise ValueError(f"Stock insuffisant pour '{product.name}'. Stock actuel: {product.quantity_in_stock}")
        product.quantity_in_stock -= quantity_change
    else:
        raise ValueError(f"Opération invalide: {operation}. Utilisez 'increase' ou 'decrease'")
    
    db.commit()
    db.refresh(product)
    
    # Vérifier et créer une alerte si nécessaire
    check_and_create_stock_alert(db, product)
    
    return product

def get_low_stock_products(db: Session, limit: int = None) -> list:
    """
    Obtenir la liste des produits avec un stock faible
    
    Args:
        db: Session de base de données
        limit: Nombre maximum de produits à retourner (optionnel)
        
    Returns:
        Liste de produits avec stock faible
    """
    
    query = db.query(Product).filter(
        Product.quantity_in_stock <= Product.minimum_stock_level,
        Product.is_active == True
    ).order_by(Product.quantity_in_stock.asc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()

def get_out_of_stock_products(db: Session) -> list:
    """
    Obtenir la liste des produits en rupture de stock
    
    Args:
        db: Session de base de données
        
    Returns:
        Liste de produits en rupture de stock
    """
    
    return db.query(Product).filter(
        Product.quantity_in_stock == 0,
        Product.is_active == True
    ).all()

def calculate_stock_value(db: Session) -> dict:
    """
    Calculer la valeur totale du stock
    
    Args:
        db: Session de base de données
        
    Returns:
        dict avec les statistiques de stock
    """
    
    from sqlalchemy import func
    from decimal import Decimal
    
    products = db.query(Product).filter(Product.is_active == True).all()
    
    total_value = Decimal('0.00')
    total_items = 0
    low_stock_count = 0
    out_of_stock_count = 0
    
    for product in products:
        total_value += product.price * product.quantity_in_stock
        total_items += product.quantity_in_stock
        
        if product.quantity_in_stock == 0:
            out_of_stock_count += 1
        elif product.quantity_in_stock <= product.minimum_stock_level:
            low_stock_count += 1
    
    return {
        "total_value": float(total_value),
        "total_items": total_items,
        "total_products": len(products),
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count
    }