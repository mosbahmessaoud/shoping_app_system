from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from utils.db import get_db
from models.client_account import ClientAccount
from models.client import Client
from schemas.client_account import (
    ClientAccountCreate,
    ClientAccountUpdate,
    ClientAccountResponse,
    ClientAccountWithClient
)

router = APIRouter(
    prefix="/client-accounts",
    tags=["Client Accounts"]
)


@router.post("/", response_model=ClientAccountResponse, status_code=status.HTTP_201_CREATED)
def create_client_account(
    account: ClientAccountCreate,
    db: Session = Depends(get_db)
):
    """Create a new client account"""
    # Check if client exists
    client = db.query(Client).filter(Client.id == account.client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with id {account.client_id} not found"
        )

    # Check if account already exists for this client
    existing_account = db.query(ClientAccount).filter(
        ClientAccount.client_id == account.client_id
    ).first()
    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account already exists for client {account.client_id}"
        )

    # Create new account
    db_account = ClientAccount(**account.dict())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


@router.get("/", response_model=List[ClientAccountWithClient])
def get_all_client_accounts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all client accounts"""
    accounts = db.query(ClientAccount).offset(skip).limit(limit).all()

    # Enrich with client data
    result = []
    for account in accounts:
        account_dict = ClientAccountResponse.from_orm(account).dict()
        if account.client:
            account_dict["client_username"] = account.client.username
            account_dict["client_email"] = account.client.email
            account_dict["client_phone_number"] = account.client.phone_number
            account_dict["client_village"] = account.client.address
        result.append(account_dict)

    return result


@router.get("/{account_id}", response_model=ClientAccountWithClient)
def get_client_account(account_id: int, db: Session = Depends(get_db)):
    """Get a specific client account by ID"""
    account = db.query(ClientAccount).filter(
        ClientAccount.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client account with id {account_id} not found"
        )

    account_dict = ClientAccountResponse.from_orm(account).dict()
    if account.client:
        account_dict["client_username"] = account.client.username
        account_dict["client_email"] = account.client.email
        account_dict["client_phone_number"] = account.client.phone_number
        account_dict["client_village"] = account.client.address

    return account_dict


@router.get("/client/{client_id}", response_model=ClientAccountWithClient)
def get_account_by_client(client_id: int, db: Session = Depends(get_db)):
    """Get client account by client ID"""
    account = db.query(ClientAccount).filter(
        ClientAccount.client_id == client_id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No account found for client {client_id}"
        )

    account_dict = ClientAccountResponse.from_orm(account).dict()
    if account.client:
        account_dict["client_username"] = account.client.username
        account_dict["client_email"] = account.client.email
        account_dict["client_phone_number"] = account.client.phone_number
        account_dict["client_village"] = account.client.address

    return account_dict


# @router.put("/{account_id}", response_model=ClientAccountResponse)
# def update_client_account(
#     account_id: int,
#     account_update: ClientAccountUpdate,
#     db: Session = Depends(get_db)
# ):
#     """
#     Update a client account - when total_remaining is modified,
#     the system will automatically adjust bill payments.
#     If total_remaining > total_amount, creates a bill for outside purchases.
#     """
#     from models.bill import Bill
#     from datetime import datetime

#     db_account = db.query(ClientAccount).filter(
#         ClientAccount.id == account_id).first()
#     if not db_account:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Client account with id {account_id} not found"
#         )

#     # Check if total_remaining is being updated
#     update_data = account_update.dict(exclude_unset=True)
#     total_remaining_changed = 'total_remaining' in update_data

#     if total_remaining_changed:
#         new_total_remaining = Decimal(str(update_data['total_remaining']))

#         if new_total_remaining < Decimal('0.00'):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Total remaining cannot be negative"
#             )

#         # Get all unpaid and partially paid bills
#         unpaid_bills = db.query(Bill).filter(
#             Bill.client_id == db_account.client_id,
#             Bill.status != "paid"
#         ).order_by(Bill.created_at).all()

#         # Calculate current total from bills
#         bills_total_amount = sum(
#             bill.total_amount for bill in unpaid_bills) if unpaid_bills else Decimal('0.00')

#         # CASE 1: new_total_remaining > bills_total_amount
#         # Client made manual purchases outside the system
#         if new_total_remaining > bills_total_amount:
#             # Calculate the difference (outside purchases amount)
#             outside_purchase_amount = new_total_remaining - bills_total_amount

#             # Check if there's already an "Outside Purchases" bill
#             existing_outside_bill = db.query(Bill).filter(
#                 Bill.client_id == db_account.client_id,
#                 Bill.bill_number.like("Achats Hors Système%"),
#                 Bill.status != "paid"
#             ).first()

#             if existing_outside_bill:
#                 # Update existing outside purchases bill
#                 existing_outside_bill.total_amount = outside_purchase_amount
#                 existing_outside_bill.total_remaining = outside_purchase_amount
#                 existing_outside_bill.total_paid = Decimal('0.00')
#                 existing_outside_bill.status = "not paid"
#                 existing_outside_bill.updated_at = datetime.utcnow()
#             else:
#                 # Create new bill for outside purchases
#                 outside_bill = Bill(
#                     client_id=db_account.client_id,
#                     bill_number=f"Achats Hors Système - {datetime.now().strftime('%d/%m/%Y')}",
#                     total_amount=outside_purchase_amount,
#                     total_paid=Decimal('0.00'),
#                     total_remaining=outside_purchase_amount,
#                     status="not paid",
#                     created_at=datetime.utcnow()
#                 )
#                 db.add(outside_bill)

#             db.flush()

#             # Now recalculate with the new bill included
#             all_unpaid_bills = db.query(Bill).filter(
#                 Bill.client_id == db_account.client_id,
#                 Bill.status != "paid"
#             ).order_by(Bill.created_at).all()

#             # Update account totals
#             db_account.total_amount = sum(
#                 bill.total_amount for bill in all_unpaid_bills)
#             db_account.total_paid = Decimal('0.00')
#             db_account.total_remaining = sum(
#                 bill.total_remaining for bill in all_unpaid_bills)

#         # CASE 2: new_total_remaining <= bills_total_amount
#         # Normal case - calculate payment from remaining
#         else:
#             # Calculate how much has been paid
#             total_paid_amount = bills_total_amount - new_total_remaining

#             # Check if there's an "Outside Purchases" bill and remove it if exists
#             outside_bill = db.query(Bill).filter(
#                 Bill.client_id == db_account.client_id,
#                 Bill.bill_number.like("Achats Hors Système%"),
#                 Bill.status != "paid"
#             ).first()

#             if outside_bill:
#                 db.delete(outside_bill)
#                 db.flush()

#                 # Recalculate unpaid bills after deletion
#                 unpaid_bills = db.query(Bill).filter(
#                     Bill.client_id == db_account.client_id,
#                     Bill.status != "paid"
#                 ).order_by(Bill.created_at).all()

#                 bills_total_amount = sum(
#                     bill.total_amount for bill in unpaid_bills) if unpaid_bills else Decimal('0.00')
#                 total_paid_amount = bills_total_amount - new_total_remaining

#             # Reset all bills to unpaid first
#             for bill in unpaid_bills:
#                 bill.total_paid = Decimal('0.00')
#                 bill.total_remaining = bill.total_amount
#                 bill.status = "not paid"

#             # Apply payment to bills in order (oldest first)
#             remaining_to_apply = total_paid_amount

#             for bill in unpaid_bills:
#                 if remaining_to_apply <= Decimal('0.00'):
#                     break

#                 if remaining_to_apply >= bill.total_amount:
#                     # Full payment for this bill
#                     bill.total_paid = bill.total_amount
#                     bill.total_remaining = Decimal('0.00')
#                     bill.status = "paid"
#                     remaining_to_apply -= bill.total_amount
#                 else:
#                     # Partial payment for this bill
#                     bill.total_paid = remaining_to_apply
#                     bill.total_remaining = bill.total_amount - remaining_to_apply
#                     bill.status = "partially paid"
#                     remaining_to_apply = Decimal('0.00')

#             db.flush()

#             # Update account values based on actual bills
#             unpaid_bills_after = db.query(Bill).filter(
#                 Bill.client_id == db_account.client_id,
#                 Bill.status != "paid"
#             ).all()

#             db_account.total_amount = sum(
#                 bill.total_amount for bill in unpaid_bills_after)
#             db_account.total_paid = total_paid_amount
#             db_account.total_remaining = sum(
#                 bill.total_remaining for bill in unpaid_bills_after)

#     else:
#         # Update other fields normally
#         for field, value in update_data.items():
#             setattr(db_account, field, value)

#     db.commit()
#     db.refresh(db_account)
#     return db_account
@router.put("/{account_id}", response_model=ClientAccountResponse)
def update_client_account(
    account_id: int,
    account_update: ClientAccountUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a client account - when total_remaining is modified, 
    the system will automatically adjust bill payments.
    If total_remaining > total_amount, creates a bill for outside purchases.
    """
    from models.bill import Bill
    from datetime import datetime
    import uuid

    db_account = db.query(ClientAccount).filter(
        ClientAccount.id == account_id).first()
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client account with id {account_id} not found"
        )

    # Check if total_remaining is being updated
    update_data = account_update.dict(exclude_unset=True)
    total_remaining_changed = 'total_remaining' in update_data

    if total_remaining_changed:
        new_total_remaining = Decimal(str(update_data['total_remaining']))

        if new_total_remaining < Decimal('0.00'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Total remaining cannot be negative"
            )

        # Get all unpaid and partially paid bills (excluding "Outside Purchases" bills)
        unpaid_bills = db.query(Bill).filter(
            Bill.client_id == db_account.client_id,
            Bill.status != "paid",
            # Exclude outside purchase bills
            ~Bill.bill_number.like("Achats Hors Système%")
        ).order_by(Bill.created_at).all()

        # Calculate current total from bills (excluding outside purchases)
        bills_total_amount = sum(
            bill.total_amount for bill in unpaid_bills) if unpaid_bills else Decimal('0.00')

        # CASE 1: new_total_remaining > bills_total_amount
        # Client made manual purchases outside the system
        if new_total_remaining > bills_total_amount:
            # Calculate the difference (outside purchases amount)
            outside_purchase_amount = new_total_remaining - bills_total_amount

            # # Check if there's already an "Outside Purchases" bill for this client
            # existing_outside_bill = db.query(Bill).filter(
            #     Bill.client_id == db_account.client_id,
            #     Bill.bill_number.like("Achats Hors Système%"),
            #     Bill.status != "paid"
            # ).first()

            # if existing_outside_bill:
            #     # Update existing outside purchases bill
            #     existing_outside_bill.total_amount = outside_purchase_amount
            #     existing_outside_bill.total_remaining = outside_purchase_amount
            #     existing_outside_bill.total_paid = Decimal('0.00')
            #     existing_outside_bill.status = "not paid"
            #     existing_outside_bill.updated_at = datetime.utcnow()
            # else:
            # Generate unique bill number for outside purchases
            # Format: Achats Hors Système - YYYYMMDD - UNIQUEID
            date_str = datetime.now().strftime('%Y%m%d%m%s')
            # First 8 chars of UUID
            unique_id = str(uuid.uuid4())[:3].upper()
            bill_number = f"Achats Hors Système - {date_str}-{unique_id}"

            # Ensure uniqueness (very unlikely to collide, but just in case)
            counter = 1
            original_bill_number = bill_number
            while db.query(Bill).filter(Bill.bill_number == bill_number).first():
                bill_number = f"{original_bill_number}-{counter}"
                counter += 1

            # Create new bill for outside purchases
            outside_bill = Bill(
                client_id=db_account.client_id,
                bill_number=bill_number,
                total_amount=outside_purchase_amount,
                total_paid=Decimal('0.00'),
                total_remaining=outside_purchase_amount,
                status="not paid",
                created_at=datetime.utcnow()
            )
            db.add(outside_bill)

            # Reset all regular bills to unpaid (no payment applied)
            for bill in unpaid_bills:
                bill.total_paid = Decimal('0.00')
                bill.total_remaining = bill.total_amount
                bill.status = "not paid"

            db.flush()

            # Now recalculate with the new bill included
            all_unpaid_bills = db.query(Bill).filter(
                Bill.client_id == db_account.client_id,
                Bill.status != "paid"
            ).all()

            # Set total_paid to 0 (not negative) when there are outside purchases
            db_account.total_amount = sum(
                bill.total_amount for bill in all_unpaid_bills)
            db_account.total_paid = Decimal('0.00')
            db_account.total_remaining = sum(
                bill.total_remaining for bill in all_unpaid_bills)

        # CASE 2: new_total_remaining <= bills_total_amount
        # Normal case - calculate payment from remaining
        else:
            # First, check if there's an "Outside Purchases" bill and remove it
            outside_bill = db.query(Bill).filter(
                Bill.client_id == db_account.client_id,
                Bill.bill_number.like("Achats Hors Système%"),
                Bill.status != "paid"
            ).first()

            if outside_bill:
                db.delete(outside_bill)
                db.flush()

                # Recalculate unpaid bills after deletion
                unpaid_bills = db.query(Bill).filter(
                    Bill.client_id == db_account.client_id,
                    Bill.status != "paid",
                    ~Bill.bill_number.like("Achats Hors Système%")
                ).order_by(Bill.created_at).all()

                bills_total_amount = sum(
                    bill.total_amount for bill in unpaid_bills) if unpaid_bills else Decimal('0.00')

            # Calculate how much has been paid
            total_paid_amount = bills_total_amount - new_total_remaining

            # Ensure total_paid is never negative
            total_paid_amount = max(Decimal('0.00'), total_paid_amount)

            # Reset all bills to unpaid first
            for bill in unpaid_bills:
                bill.total_paid = Decimal('0.00')
                bill.total_remaining = bill.total_amount
                bill.status = "not paid"

            # Apply payment to bills in order (oldest first)
            remaining_to_apply = total_paid_amount

            for bill in unpaid_bills:
                if remaining_to_apply <= Decimal('0.00'):
                    break

                if remaining_to_apply >= bill.total_amount:
                    # Full payment for this bill
                    bill.total_paid = bill.total_amount
                    bill.total_remaining = Decimal('0.00')
                    bill.status = "paid"
                    remaining_to_apply -= bill.total_amount
                else:
                    # Partial payment for this bill
                    bill.total_paid = remaining_to_apply
                    bill.total_remaining = bill.total_amount - remaining_to_apply
                    bill.status = "partially paid"
                    remaining_to_apply = Decimal('0.00')

            db.flush()

            # Update account values based on actual bills
            unpaid_bills_after = db.query(Bill).filter(
                Bill.client_id == db_account.client_id,
                Bill.status != "paid"
            ).all()

            db_account.total_amount = sum(
                bill.total_amount for bill in unpaid_bills_after)
            db_account.total_paid = total_paid_amount
            db_account.total_remaining = sum(
                bill.total_remaining for bill in unpaid_bills_after)

    else:
        # Update other fields normally
        for field, value in update_data.items():
            setattr(db_account, field, value)

    db.commit()
    db.refresh(db_account)
    return db_account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client_account(account_id: int, db: Session = Depends(get_db)):
    """Delete a client account"""
    db_account = db.query(ClientAccount).filter(
        ClientAccount.id == account_id).first()
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client account with id {account_id} not found"
        )

    db.delete(db_account)
    db.commit()
    return None


@router.post("/recalculate/{client_id}", response_model=ClientAccountResponse)
def recalculate_client_account(client_id: int, db: Session = Depends(get_db)):
    """
    Recalculate client account totals from all bills.
    This syncs the account with actual bill data without modifying bill payments.
    """
    from models.bill import Bill

    # Get or create account
    account = db.query(ClientAccount).filter(
        ClientAccount.client_id == client_id
    ).first()

    if not account:
        # Check if client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with id {client_id} not found"
            )

        # Create new account
        account = ClientAccount(
            client_id=client_id,
            total_amount=Decimal('0.00'),
            total_paid=Decimal('0.00'),
            total_remaining=Decimal('0.00')
        )
        db.add(account)
        db.flush()

    # Get only unpaid and partially paid bills
    unpaid_bills = db.query(Bill).filter(
        Bill.client_id == client_id,
        Bill.status != "paid"
    ).all()

    # Calculate totals from bills
    total_amount = sum(bill.total_amount for bill in unpaid_bills)
    total_paid = sum(bill.total_paid for bill in unpaid_bills)
    total_remaining = sum(bill.total_remaining for bill in unpaid_bills)

    # Update account with calculated values
    account.total_amount = Decimal(str(total_amount))
    account.total_paid = Decimal(str(total_paid))
    account.total_remaining = Decimal(str(total_remaining))

    db.commit()
    db.refresh(account)
    return account
