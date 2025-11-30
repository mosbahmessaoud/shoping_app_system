
# schemas/otp.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

class OTPRequest(BaseModel):
    email: EmailStr
    otp_type: str  # 'registration' or 'password_reset'

class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str
    otp_type: str

class OTPResponse(BaseModel):
    message: str
    email: str

class PasswordReset(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str