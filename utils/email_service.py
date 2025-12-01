# utils/email_service.py
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


class EmailService:
    def __init__(self):
        # Maileroo SMTP Configuration
        self.smtp_server = "smtp.maileroo.com"
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_name = os.getenv("SENDER_NAME", "E-Commerce App")

        # Validate configuration
        if self.smtp_username and self.smtp_password:
            print("✅ Maileroo SMTP configured")
        else:
            print("⚠️ WARNING: SMTP credentials not set!")

    def send_otp_email(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
        """Send OTP via Maileroo SMTP"""
        try:
            # Validate credentials
            if not self.smtp_username or not self.smtp_password or not self.sender_email:
                print("❌ ERROR: SMTP credentials not configured")
                print(f"   Username set: {bool(self.smtp_username)}")
                print(f"   Password set: {bool(self.smtp_password)}")
                print(f"   Sender Email set: {bool(self.sender_email)}")
                return False

            # Determine subject and title
            if otp_type == "registration":
                subject = "Code de vérification - E-Commerce"
                title = "Vérification de votre compte"
            elif otp_type == "password_reset":
                subject = "Réinitialisation de mot de passe - E-Commerce"
                title = "Réinitialisation de mot de passe"
            else:
                subject = "Code de vérification"
                title = "Vérification"

            # HTML email content
            html_content = f"""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
                <table role="presentation" style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td align="center" style="padding: 40px 0;">
                            <table role="presentation" style="width: 600px; max-width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                
                                <!-- Header -->
                                <tr>
                                    <td style="padding: 40px 40px 20px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px 10px 0 0;">
                                        <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600;">🛍️ E-Commerce</h1>
                                    </td>
                                </tr>
                                
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px;">
                                        <h2 style="margin: 0 0 20px; color: #333333; font-size: 24px; font-weight: 600;">{title}</h2>
                                        
                                        <p style="margin: 0 0 20px; color: #666666; font-size: 16px; line-height: 1.6;">
                                            Votre code de vérification est :
                                        </p>
                                        
                                        <!-- OTP Code -->
                                        <table role="presentation" style="width: 100%; margin: 30px 0;">
                                            <tr>
                                                <td align="center" style="padding: 25px; background-color: #f8f9fa; border-radius: 8px; border: 2px dashed #667eea;">
                                                    <span style="font-size: 40px; font-weight: bold; color: #667eea; letter-spacing: 10px; font-family: 'Courier New', monospace;">
                                                        {otp_code}
                                                    </span>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <p style="margin: 20px 0; color: #666666; font-size: 14px; line-height: 1.6;">
                                            ⏰ <strong>Ce code expire dans 10 minutes.</strong>
                                        </p>
                                        
                                        <p style="margin: 20px 0; color: #999999; font-size: 14px; line-height: 1.6;">
                                            Si vous n'avez pas demandé ce code, veuillez ignorer cet email.
                                        </p>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="padding: 20px 40px; background-color: #f8f9fa; border-radius: 0 0 10px 10px; text-align: center;">
                                        <p style="margin: 0; color: #999999; font-size: 12px;">
                                            © 2024 E-Commerce App. Tous droits réservés.
                                        </p>
                                        <p style="margin: 10px 0 0 0; color: #999999; font-size: 12px;">
                                            Envoyé via Maileroo
                                        </p>
                                    </td>
                                </tr>
                                
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = recipient_email

            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            print(f"📧 Sending email to {recipient_email} via Maileroo SMTP...")
            print(f"   Server: {self.smtp_server}:{self.smtp_port}")
            print(f"   From: {self.sender_name} <{self.sender_email}>")

            # Send email via SMTP
            if self.smtp_port == 465:
                # SSL connection
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)
            else:
                # TLS connection (port 587)
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)

            print(f"✅ Email sent successfully to {recipient_email}!")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ SMTP Authentication Error: {e}")
            print("   Check your SMTP_USERNAME and SMTP_PASSWORD")
            return False

        except smtplib.SMTPException as e:
            print(f"❌ SMTP Error: {type(e).__name__}: {str(e)}")
            return False

        except Exception as e:
            print(f"❌ Error sending email via Maileroo:")
            print(f"   Type: {type(e).__name__}")
            print(f"   Message: {str(e)}")
            return False
