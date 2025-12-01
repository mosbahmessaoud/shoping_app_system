# utils/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv("SENDER_PASSWORD")

    def send_otp_email(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
        """Send OTP via email"""
        try:
            # Validate configuration
            if not self.sender_email or not self.sender_password:
                print("ERROR: SENDER_EMAIL or SENDER_PASSWORD not configured")
                return False

            subject = "Code de vérification" if otp_type == "registration" else "Réinitialisation du mot de passe"

            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>{'Vérification de votre compte' if otp_type == 'registration' else 'Réinitialisation de mot de passe'}</h2>
                    <p>Votre code de vérification est:</p>
                    <h1 style="color: #4CAF50; font-size: 32px; letter-spacing: 5px;">{otp_code}</h1>
                    <p>Ce code expire dans 10 minutes.</p>
                    <p>Si vous n'avez pas demandé ce code, veuillez ignorer cet email.</p>
                </body>
            </html>
            """

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email

            html_part = MIMEText(body, "html")
            message.attach(html_part)

            print(
                f"Attempting to send email to {recipient_email} via {self.smtp_server}:{self.smtp_port}")

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)

            print(f"Email sent successfully to {recipient_email}")
            return True

        except Exception as e:
            print(f"Error sending email: {type(e).__name__}: {str(e)}")
            return False
