# utils/email_service.py
import resend
import os
from typing import Optional


class EmailService:
    def __init__(self):
        # Set your Resend API key
        resend.api_key = os.getenv("RESEND_API_KEY")

        # Use onboarding@resend.dev for testing without custom domain
        # This email can send up to 100 emails/day for free
        self.from_email = "onboarding@resend.dev"

        # Your app name for email branding
        self.app_name = "iTriDevel"

    def send_otp_email(self, to_email: str, otp_code: str, otp_type: str) -> bool:
        """Send OTP verification email"""
        try:
            # Determine email content based on OTP type
            if otp_type == "registration":
                subject = f"Code de vérification - {self.app_name}"
                html_content = self._get_registration_template(otp_code)
            elif otp_type == "password_reset":
                subject = f"Réinitialisation du mot de passe - {self.app_name}"
                html_content = self._get_password_reset_template(otp_code)
            else:
                return False

            # Send email using Resend
            params = {
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            response = resend.Emails.send(params)

            # Check if email was sent successfully
            return response.get("id") is not None

        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def _get_registration_template(self, otp_code: str) -> str:
        """HTML template for registration OTP"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Bienvenue sur {self.app_name}!</h1>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Code de vérification</h2>
                <p>Merci de vous inscrire! Utilisez le code ci-dessous pour vérifier votre email:</p>
                
                <div style="background: white; padding: 20px; text-align: center; border-radius: 8px; margin: 25px 0; border: 2px solid #667eea;">
                    <h1 style="font-size: 36px; letter-spacing: 8px; margin: 0; color: #667eea;">{otp_code}</h1>
                </div>
                
                <p style="color: #666; font-size: 14px;">Ce code expirera dans <strong>10 minutes</strong>.</p>
                <p style="color: #666; font-size: 14px;">Si vous n'avez pas demandé ce code, vous pouvez ignorer cet email.</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    Cet email a été envoyé par {self.app_name}<br>
                    Ne partagez jamais votre code de vérification avec quiconque.
                </p>
            </div>
        </body>
        </html>
        """

    def _get_password_reset_template(self, otp_code: str) -> str:
        """HTML template for password reset OTP"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Réinitialisation du mot de passe</h1>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Code de vérification</h2>
                <p>Vous avez demandé la réinitialisation de votre mot de passe. Utilisez le code ci-dessous:</p>
                
                <div style="background: white; padding: 20px; text-align: center; border-radius: 8px; margin: 25px 0; border: 2px solid #f5576c;">
                    <h1 style="font-size: 36px; letter-spacing: 8px; margin: 0; color: #f5576c;">{otp_code}</h1>
                </div>
                
                <p style="color: #666; font-size: 14px;">Ce code expirera dans <strong>10 minutes</strong>.</p>
                
                <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; color: #856404; font-size: 14px;">
                        <strong>⚠️ Important:</strong> Si vous n'avez pas demandé cette réinitialisation, 
                        veuillez ignorer cet email et sécuriser votre compte immédiatement.
                    </p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    Cet email a été envoyé par {self.app_name}<br>
                    Ne partagez jamais votre code de vérification avec quiconque.
                </p>
            </div>
        </body>
        </html>
        """
