# utils/email_service.py
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465  # Try SSL port instead of TLS
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv(
            "SENDER_PASSWORD")  # Gmail App Password

    def send_otp_email(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
        try:
            if not self.sender_email or not self.sender_password:
                print("ERROR: Email credentials not configured")
                return False

            subject = "Code de vérification" if otp_type == "registration" else "Réinitialisation du mot de passe"

            html_content = f"""
            <html>
            <body>
                <h2>{'Vérification de votre compte' if otp_type == 'registration' else 'Réinitialisation de mot de passe'}</h2>
                <p>Votre code de vérification est:</p>
                <h1>{otp_code}</h1>
                <p>Ce code expire dans 10 minutes.</p>
            </body>
            </html>
            """

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email
            message.attach(MIMEText(html_content, "html"))

            # Use SSL connection on port 465
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)

            print(f"Email sent successfully to {recipient_email}")
            return True

        except Exception as e:
            print(f"Error sending email: {type(e).__name__}: {str(e)}")
            return False
