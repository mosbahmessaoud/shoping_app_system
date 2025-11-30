from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from models.payment import Payment
from models.bill import Bill
from schemas.payment import PaymentCreate, PaymentUpdate, PaymentResponse, PaymentHistory
from utils.db import get_db
from utils.auth import get_current_admin

router = APIRouter(prefix="/payment", tags=["Payment"])

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    payment_data: PaymentCreate,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Créer un nouveau paiement (admin seulement)"""
    
    # Vérifier si la facture existe
    bill = db.query(Bill).filter(Bill.id == payment_data.bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture non trouvée"
        )
    
    # Vérifier que le montant du paiement ne dépasse pas le montant restant
    if payment_data.amount_paid > bill.total_remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le montant du paiement ({payment_data.amount_paid}) dépasse le montant restant ({bill.total_remaining})"
        )
    
    # Créer le paiement
    new_payment = Payment(
        bill_id=payment_data.bill_id,
        admin_id=current_admin.id,
        amount_paid=payment_data.amount_paid,
        payment_method=payment_data.payment_method,
        notes=payment_data.notes,
        payment_date=payment_data.payment_date
    )
    
    db.add(new_payment)
    
    # Mettre à jour les totaux de la facture
    bill.total_paid += payment_data.amount_paid
    bill.total_remaining -= payment_data.amount_paid
    
    # Mettre à jour le statut de la facture
    if bill.total_remaining <= Decimal('0.00'):
        bill.status = "paid"
    else:
        bill.status = "not paid"
    
    db.commit()
    db.refresh(new_payment)
    
    return new_payment

@router.get("/bill/{bill_id}", response_model=PaymentHistory)
def get_bill_payment_history(
    bill_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir l'historique des paiements d'une facture (admin seulement)"""
    
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture non trouvée"
        )
    
    payments = db.query(Payment).filter(Payment.bill_id == bill_id).all()
    
    return PaymentHistory(
        bill_id=bill.id,
        bill_number=bill.bill_number,
        total_amount=bill.total_amount,
        total_paid=bill.total_paid,
        total_remaining=bill.total_remaining,
        payments=[PaymentResponse(
            id=p.id,
            bill_id=p.bill_id,
            admin_id=p.admin_id,
            amount_paid=p.amount_paid,
            payment_method=p.payment_method,
            notes=p.notes,
            payment_date=p.payment_date,
            created_at=p.created_at
        ) for p in payments]
    )

@router.get("/", response_model=List[PaymentResponse])
def get_all_payments(
    skip: int = 0,
    limit: int = 100,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir tous les paiements (admin seulement)"""
    
    payments = db.query(Payment).offset(skip).limit(limit).all()
    return payments

@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment_by_id(
    payment_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Obtenir un paiement par son ID (admin seulement)"""
    
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paiement non trouvé"
        )
    
    return payment

@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Mettre à jour un paiement (admin seulement)"""
    
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paiement non trouvé"
        )
    
    bill = db.query(Bill).filter(Bill.id == payment.bill_id).first()
    
    # Si le montant change, recalculer les totaux de la facture
    if payment_data.amount_paid and payment_data.amount_paid != payment.amount_paid:
        # Restaurer l'ancien montant
        bill.total_paid -= payment.amount_paid
        bill.total_remaining += payment.amount_paid
        
        # Appliquer le nouveau montant
        if payment_data.amount_paid > bill.total_remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le nouveau montant ({payment_data.amount_paid}) dépasse le montant restant ({bill.total_remaining})"
            )
        
        bill.total_paid += payment_data.amount_paid
        bill.total_remaining -= payment_data.amount_paid
        payment.amount_paid = payment_data.amount_paid
        
        # Mettre à jour le statut
        if bill.total_remaining <= Decimal('0.00'):
            bill.status = "paid"
        else:
            bill.status = "not paid"
    
    # Mettre à jour les autres champs
    if payment_data.payment_method is not None:
        payment.payment_method = payment_data.payment_method
    if payment_data.notes is not None:
        payment.notes = payment_data.notes
    if payment_data.payment_date is not None:
        payment.payment_date = payment_data.payment_date
    
    db.commit()
    db.refresh(payment)
    
    return payment

@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(
    payment_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Supprimer un paiement (admin seulement)"""
    
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paiement non trouvé"
        )
    
    # Restaurer les totaux de la facture
    bill = db.query(Bill).filter(Bill.id == payment.bill_id).first()
    bill.total_paid -= payment.amount_paid
    bill.total_remaining += payment.amount_paid
    
    # Mettre à jour le statut
    if bill.total_remaining > Decimal('0.00'):
        bill.status = "not paid"
    
    db.delete(payment)
    db.commit()
    
    return None