# utils/email_service.py
import os
import resend
from typing import Optional


class EmailService:
    def __init__(self):
        self.email_provider = os.getenv("EMAIL_PROVIDER", "smtp")

        if self.email_provider == "resend":
            resend.api_key = os.getenv("RESEND_API_KEY")
            self.sender_email = os.getenv(
                "SENDER_EMAIL", "onboarding@resend.dev")

            print("=" * 60)
            print("📧 EMAIL SERVICE CONFIGURATION (RESEND)")
            print("=" * 60)
            print(f"Sender Email: {self.sender_email}")
            print(
                f"API Key Configured: {'✅ Yes' if resend.api_key else '❌ No'}")
            if resend.api_key:
                print(
                    f"API Key Preview: {resend.api_key[:7]}...{resend.api_key[-4:]}")
            print("=" * 60)
        else:
            # Keep SMTP for local development
            import smtplib
            self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
            self.sender_email = os.getenv("SENDER_EMAIL")
            self.sender_password = os.getenv("SENDER_PASSWORD")

            print("=" * 60)
            print("📧 EMAIL SERVICE CONFIGURATION (SMTP)")
            print("=" * 60)
            print(f"SMTP Server: {self.smtp_server}")
            print(f"SMTP Port: {self.smtp_port}")
            print(f"Sender Email: {self.sender_email}")
            print(
                f"Password Configured: {'✅ Yes' if self.sender_password else '❌ No'}")
            print("=" * 60)

    def send_otp_email(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
        """Send OTP via email using configured provider"""
        if self.email_provider == "resend":
            return self._send_via_resend(recipient_email, otp_code, otp_type)
        else:
            return self._send_via_smtp(recipient_email, otp_code, otp_type)

    def _send_via_resend(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
        """Send email via Resend API"""
        try:
            print("\n" + "=" * 60)
            print("📤 SENDING EMAIL VIA RESEND")
            print("=" * 60)
            print(f"📧 To: {recipient_email}")
            print(f"📧 From: {self.sender_email}")
            print(f"🔐 OTP Code: {otp_code}")
            print(f"📝 OTP Type: {otp_type}")

            subject = "Code de vérification" if otp_type == "registration" else "Réinitialisation du mot de passe"
            print(f"📋 Subject: {subject}")

            html_content = f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                </head>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h2 style="color: #333; margin-bottom: 20px;">
                            {'Vérification de votre compte' if otp_type == 'registration' else 'Réinitialisation de mot de passe'}
                        </h2>
                        <p style="color: #666; font-size: 16px; line-height: 1.5;">
                            Votre code de vérification est:
                        </p>
                        <div style="background-color: #f0f0f0; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0;">
                            <h1 style="color: #4CAF50; font-size: 36px; letter-spacing: 8px; margin: 0;">
                                {otp_code}
                            </h1>
                        </div>
                        <p style="color: #666; font-size: 14px; line-height: 1.5;">
                            Ce code expire dans <strong>10 minutes</strong>.
                        </p>
                        <p style="color: #999; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                            Si vous n'avez pas demandé ce code, veuillez ignorer cet email.
                        </p>
                    </div>
                </body>
            </html>
            """

            print("📨 Sending via Resend API...")

            params = {
                "from": self.sender_email,
                "to": [recipient_email],
                "subject": subject,
                "html": html_content,
            }

            email = resend.Emails.send(params)

            print(f"✅ Email sent successfully!")
            print(f"📬 Message ID: {email.get('id', 'N/A')}")
            print("=" * 60 + "\n")
            return True

        except Exception as e:
            print("\n" + "=" * 60)
            print("❌ RESEND API ERROR")
            print("=" * 60)
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Details: {str(e)}")
            print("\n📋 TROUBLESHOOTING:")
            print("1. Check your RESEND_API_KEY in Railway variables")
            print("2. Verify your sender email/domain is configured in Resend")
            print("3. Check Resend dashboard: https://resend.com/emails")
            print("=" * 60 + "\n")
            return False

    def _send_via_smtp(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
        """Send email via SMTP (for local development)"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        try:
            print("\n" + "=" * 60)
            print("📤 SENDING EMAIL VIA SMTP")
            print("=" * 60)

            if not self.sender_email or not self.sender_password:
                print("❌ ERROR: SENDER_EMAIL or SENDER_PASSWORD not configured")
                return False

            print(f"📧 To: {recipient_email}")
            print(f"📧 From: {self.sender_email}")
            print(f"🔐 OTP Code: {otp_code}")
            print(f"🌐 SMTP Server: {self.smtp_server}:{self.smtp_port}")

            subject = "Code de vérification" if otp_type == "registration" else "Réinitialisation du mot de passe"

            html_content = f"""
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
            message.attach(MIMEText(html_content, "html"))

            print("🔌 Connecting to SMTP server...")
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                print("✅ Connected")
                server.starttls()
                print("✅ TLS enabled")
                server.login(self.sender_email, self.sender_password)
                print("✅ Authenticated")
                server.send_message(message)
                print("✅ Email sent successfully!")

            print("=" * 60 + "\n")
            return True

        except Exception as e:
            print(f"\n❌ SMTP Error: {type(e).__name__}: {str(e)}\n")
            return False
