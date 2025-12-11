# # routes/otp.py
# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from models.admin import Admin
# from models.client import Client
# from schemas.otp import OTPRequest, OTPVerify, OTPResponse, PasswordReset
# from utils.db import get_db
# from utils.otp_service import OTPService
# from utils.email_service import EmailService
# from utils.auth import hash_password

# router = APIRouter(prefix="/otp", tags=["OTP"])
# email_service = EmailService()


# @router.post("/send", response_model=OTPResponse)
# def send_otp(otp_request: OTPRequest, db: Session = Depends(get_db)):
#     """Send OTP to email"""

#     print("\n" + "🔵" * 30)
#     print("🔵 NEW OTP REQUEST RECEIVED")
#     print("🔵" * 30)
#     print(f"📧 Email: {otp_request.email}")
#     print(f"📝 OTP Type: {otp_request.otp_type}")
#     print("🔵" * 30 + "\n")

#     print("🔍 Checking if email exists in database...")
#     client = db.query(Client).filter(Client.email == otp_request.email).first()
#     admin = db.query(Admin).filter(Admin.email == otp_request.email).first()

#     print(f"   Client found: {'✅ Yes' if client else '❌ No'}")
#     print(f"   Admin found: {'✅ Yes' if admin else '❌ No'}")

#     if otp_request.otp_type == "registration":
#         if client or admin:
#             print("❌ Registration failed: Email already exists")
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Cet email est déjà utilisé"
#             )
#         print("✅ Email available for registration")

#     elif otp_request.otp_type == "password_reset":
#         if not client and not admin:
#             print("❌ Password reset failed: No account found")
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Aucun compte trouvé avec cet email"
#             )
#         print("✅ Account found for password reset")

#     else:
#         print(f"❌ Invalid OTP type: {otp_request.otp_type}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Type d'OTP invalide"
#         )

#     # Generate and store OTP
#     print("\n🔐 Generating OTP code...")
#     otp_code = OTPService.create_otp(
#         db, otp_request.email, otp_request.otp_type)
#     print(f"✅ OTP generated: {otp_code}")
#     print(f"💾 OTP saved to database for: {otp_request.email}")

#     # Send email
#     print("\n📤 Attempting to send email...")
#     email_sent = email_service.send_otp_email(
#         otp_request.email,
#         otp_code,
#         otp_request.otp_type
#     )

#     if not email_sent:
#         print("❌ EMAIL SENDING FAILED!")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Erreur lors de l'envoi de l'email"
#         )

#     print("✅ OTP REQUEST COMPLETED SUCCESSFULLY\n")
#     return {
#         "message": "Code OTP envoyé avec succès",
#         "email": otp_request.email
#     }


# @router.post("/verify", response_model=OTPResponse)
# def verify_otp(otp_verify: OTPVerify, db: Session = Depends(get_db)):
#     """Verify OTP code"""

#     print("\n" + "🟢" * 30)
#     print("🟢 OTP VERIFICATION REQUEST")
#     print("🟢" * 30)
#     print(f"📧 Email: {otp_verify.email}")
#     print(f"🔐 OTP Code: {otp_verify.otp_code}")
#     print(f"📝 OTP Type: {otp_verify.otp_type}")
#     print("🟢" * 30 + "\n")

#     is_valid = OTPService.verify_otp(
#         db,
#         otp_verify.email,
#         otp_verify.otp_code,
#         otp_verify.otp_type
#     )

#     if not is_valid:
#         print("❌ OTP verification failed: Invalid or expired code")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Code OTP invalide ou expiré"
#         )

#     print("✅ OTP VERIFIED SUCCESSFULLY\n")
#     return {
#         "message": "OTP vérifié avec succès",
#         "email": otp_verify.email
#     }


# @router.post("/reset-password", response_model=OTPResponse)
# def reset_password(reset_data: PasswordReset, db: Session = Depends(get_db)):
#     """Reset password using OTP"""

#     print("\n" + "🟡" * 30)
#     print("🟡 PASSWORD RESET REQUEST")
#     print("🟡" * 30)
#     print(f"📧 Email: {reset_data.email}")
#     print(f"🔐 OTP Code: {reset_data.otp_code}")
#     print("🟡" * 30 + "\n")

#     # Verify OTP first
#     print("🔍 Verifying OTP...")
#     is_valid = OTPService.verify_otp(
#         db,
#         reset_data.email,
#         reset_data.otp_code,
#         "password_reset"
#     )

#     if not is_valid:
#         print("❌ OTP verification failed")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Code OTP invalide ou expiré"
#         )

#     print("✅ OTP verified successfully")

#     # Update password
#     print("🔍 Finding user account...")
#     client = db.query(Client).filter(Client.email == reset_data.email).first()
#     admin = db.query(Admin).filter(Admin.email == reset_data.email).first()

#     if not client and not admin:
#         print("❌ No account found")
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Client non trouvé"
#         )

#     print("🔒 Updating password...")
#     if client:
#         print(f"   Updating password for client: {client.email}")
#         client.password_hash = hash_password(reset_data.new_password)
#     elif admin:
#         print(f"   Updating password for admin: {admin.email}")
#         admin.password_hash = hash_password(reset_data.new_password)

#     db.commit()
#     print("✅ PASSWORD RESET COMPLETED SUCCESSFULLY\n")

#     return {
#         "message": "Mot de passe réinitialisé avec succès",
#         "email": reset_data.email
#     }
