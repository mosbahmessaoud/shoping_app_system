
# routes/otp.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.admin import Admin
from models.client import Client
from schemas.otp import OTPRequest, OTPVerify, OTPResponse, PasswordReset
from utils.db import get_db
from utils.otp_service import OTPService
from utils.email_service import EmailService
from utils.auth import hash_password

router = APIRouter(prefix="/otp", tags=["OTP"])
email_service = EmailService()


@router.post("/send", response_model=OTPResponse)
def send_otp(otp_request: OTPRequest, db: Session = Depends(get_db)):
    """Send OTP to email"""

    client = db.query(Client).filter(Client.email == otp_request.email).first()
    admin = db.query(Admin).filter(Admin.email == otp_request.email).first()

    if otp_request.otp_type == "registration":
        if client or admin :
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé"
            )
    elif otp_request.otp_type == "password_reset":
        if not client and not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun compte trouvé avec cet email"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type d'OTP invalide"
        )

    # Generate and store OTP
    otp_code = OTPService.create_otp(
        db, otp_request.email, otp_request.otp_type)

    # Send email
    email_sent = email_service.send_otp_email(
        otp_request.email,
        otp_code,
        otp_request.otp_type
    )

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'envoi de l'email"
        )

    return {
        "message": "Code OTP envoyé avec succès",
        "email": otp_request.email
    }


@router.post("/verify", response_model=OTPResponse)
def verify_otp(otp_verify: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP code"""

    is_valid = OTPService.verify_otp(
        db,
        otp_verify.email,
        otp_verify.otp_code,
        otp_verify.otp_type
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code OTP invalide ou expiré"
        )

    return {
        "message": "OTP vérifié avec succès",
        "email": otp_verify.email
    }


@router.post("/reset-password", response_model=OTPResponse)
def reset_password(reset_data: PasswordReset, db: Session = Depends(get_db)):
    """Reset password using OTP"""

    # Verify OTP first
    is_valid = OTPService.verify_otp(
        db,
        reset_data.email,
        reset_data.otp_code,
        "password_reset"
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code OTP invalide ou expiré"
        )

    # Update password
    client = db.query(Client).filter(Client.email == reset_data.email).first()
    admin = db.query(Admin).filter(Admin.email == reset_data.email).first()


    if not client and not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client non trouvé"
        )

    if client :
        client.password_hash = hash_password(reset_data.new_password)
    elif admin :
        admin.password_hash = hash_password(reset_data.new_password)

    db.commit()

    return {
        "message": "Mot de passe réinitialisé avec succès",
        "email": reset_data.email
    }
