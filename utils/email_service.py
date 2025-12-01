# utils/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv("SENDER_PASSWORD")

        # Debug: Print configuration (mask password)
        print("=" * 60)
        print("📧 EMAIL SERVICE CONFIGURATION")
        print("=" * 60)
        print(f"SMTP Server: {self.smtp_server}")
        print(f"SMTP Port: {self.smtp_port}")
        print(f"Sender Email: {self.sender_email}")
        print(
            f"Password Configured: {'✅ Yes' if self.sender_password else '❌ No'}")
        if self.sender_password:
            print(f"Password Length: {len(self.sender_password)} characters")
            print(
                f"Password Preview: {self.sender_password[:3]}{'*' * (len(self.sender_password) - 3)}")
        print("=" * 60)

    def send_otp_email(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
        """Send OTP via email"""
        try:
            print("\n" + "=" * 60)
            print("📤 ATTEMPTING TO SEND EMAIL")
            print("=" * 60)

            # Validate configuration
            if not self.sender_email or not self.sender_password:
                print("❌ ERROR: SENDER_EMAIL or SENDER_PASSWORD not configured")
                print(f"   SENDER_EMAIL: {self.sender_email}")
                print(
                    f"   SENDER_PASSWORD: {'Set' if self.sender_password else 'Not Set'}")
                return False

            print(f"📧 To: {recipient_email}")
            print(f"📧 From: {self.sender_email}")
            print(f"🔐 OTP Code: {otp_code}")
            print(f"📝 OTP Type: {otp_type}")
            print(f"🌐 SMTP Server: {self.smtp_server}:{self.smtp_port}")

            subject = "Code de vérification" if otp_type == "registration" else "Réinitialisation du mot de passe"
            print(f"📋 Subject: {subject}")

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

            print("✅ Email message created successfully")
            print(
                f"🔌 Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}...")

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                print("✅ Connected to SMTP server")

                print("🔒 Starting TLS encryption...")
                server.starttls()
                print("✅ TLS encryption enabled")

                print(f"🔑 Authenticating with email: {self.sender_email}")
                print(
                    f"🔑 Password length: {len(self.sender_password)} characters")

                server.login(self.sender_email, self.sender_password)
                print("✅ Authentication successful!")

                print("📨 Sending email...")
                server.send_message(message)
                print("✅ Email sent successfully!")

            print("=" * 60)
            print(f"✅ EMAIL SENT SUCCESSFULLY TO {recipient_email}")
            print("=" * 60 + "\n")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print("\n" + "=" * 60)
            print("❌ SMTP AUTHENTICATION ERROR")
            print("=" * 60)
            print(f"Error Code: {e.smtp_code}")
            print(
                f"Error Message: {e.smtp_error.decode() if hasattr(e.smtp_error, 'decode') else e.smtp_error}")
            print("\n📋 TROUBLESHOOTING STEPS:")
            print("1. ✅ Enable 2-Factor Authentication on your Google Account")
            print("2. 🔑 Generate an App Password:")
            print("   → Go to: https://myaccount.google.com/apppasswords")
            print("   → Select 'Mail' and your device")
            print("   → Copy the 16-character password")
            print("3. 📝 Update your .env file:")
            print(f"   SENDER_EMAIL={self.sender_email}")
            print("   SENDER_PASSWORD=your-16-char-app-password")
            print("4. 🔄 Restart your application")
            print("\n⚠️  DO NOT use your regular Gmail password!")
            print("=" * 60 + "\n")
            return False

        except smtplib.SMTPException as e:
            print("\n" + "=" * 60)
            print("❌ SMTP ERROR")
            print("=" * 60)
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Details: {str(e)}")
            print("=" * 60 + "\n")
            return False

        except Exception as e:
            print("\n" + "=" * 60)
            print("❌ UNEXPECTED ERROR")
            print("=" * 60)
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Details: {str(e)}")
            print(f"Error Args: {e.args}")
            print("=" * 60 + "\n")
            return False
