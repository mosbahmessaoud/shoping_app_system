# models/otp.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func

from utils.db import Base

class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    otp_code = Column(String(6), nullable=False)
    otp_type = Column(String(50), nullable=False)  # 'registration' or 'password_reset'
    is_used = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


