from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.orm import joinedload

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


@router.put("/{account_id}", response_model=ClientAccountResponse)
def update_client_account(
    account_id: int,
    account_update: ClientAccountUpdate,
    db: Session = Depends(get_db)
):
    """Update a client account"""
    db_account = db.query(ClientAccount).filter(
        ClientAccount.id == account_id).first()
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client account with id {account_id} not found"
        )

    # Update only provided fields
    update_data = account_update.dict(exclude_unset=True)
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
    """Recalculate client account totals from all bills"""
    from models.bill import Bill
    from decimal import Decimal

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
        account = ClientAccount(client_id=client_id)
        db.add(account)

    # Get all bills for this client
    bills = db.query(Bill).filter(Bill.client_id == client_id,
                                  Bill.status != "paid").all()

    # Calculate totals
    total_amount = sum(bill.total_amount for bill in bills)
    # total_paid = sum(bill.total_paid for bill in bills)
    total_remaining = sum(bill.total_remaining for bill in bills)

    # Update account
    account.total_amount = Decimal(str(total_amount))
    # account.total_paid = Decimal(str(total_paid))
    account.total_remaining = Decimal(str(total_remaining))

    db.commit()
    db.refresh(account)
    return account
