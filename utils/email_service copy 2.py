# # utils/email_service.py
# import os
# import resend

# class EmailService:
#     def __init__(self):
#         resend.api_key = os.getenv("RESEND_API_KEY")
#         self.sender_email = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")
    
#     def send_otp_email(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
#         try:
#             subject = "Code de vérification" if otp_type == "registration" else "Réinitialisation du mot de passe"

#             html_content = f"""
#             <h2>{'Vérification de votre compte' if otp_type == 'registration' else 'Réinitialisation de mot de passe'}</h2>
#             <p>Votre code de vérification est:</p>
#             <h1 style="color: #4CAF50; font-size: 36px; letter-spacing: 8px;">{otp_code}</h1>
#             <p>Ce code expire dans 10 minutes.</p>
#             """

#             params = {
#                 "from": self.sender_email,
#                 "to": [recipient_email],
#                 "subject": subject,
#                 "html": html_content
#             }

#             resend.Emails.send(params)
#             print(f"✅ Email sent to {recipient_email}")
#             return True

#         except Exception as e:
#             print(f"❌ Error: {e}")
#             return False