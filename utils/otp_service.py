

# utils/otp_service.py
import random
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.otp import OTP

class OTPService:
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a random OTP code"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def create_otp(db: Session, email: str, otp_type: str) -> str:
        """Create and store OTP in database"""
        # Invalidate previous OTPs for this email and type
        db.query(OTP).filter(
            OTP.email == email,
            OTP.otp_type == otp_type,
            OTP.is_used == False
        ).update({"is_used": True})
        
        # Generate new OTP
        otp_code = OTPService.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        new_otp = OTP(
            email=email,
            otp_code=otp_code,
            otp_type=otp_type,
            expires_at=expires_at
        )
        
        db.add(new_otp)
        db.commit()
        
        return otp_code
    
    @staticmethod
    def verify_otp(db: Session, email: str, otp_code: str, otp_type: str) -> bool:
        """Verify OTP code"""
        otp = db.query(OTP).filter(
            OTP.email == email,
            OTP.otp_code == otp_code,
            OTP.otp_type == otp_type,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        ).first()
        
        if otp:
            otp.is_used = True
            otp.is_verified = True
            db.commit()
            return True
        
        return False