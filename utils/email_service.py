# utils/email_service.py
import os
import resend


class EmailService:
    def __init__(self):
        # Set the Resend API key from environment variable
        api_key = os.getenv("RESEND_API_KEY")

        if api_key:
            resend.api_key = api_key
            print("✅ Resend API key configured")
        else:
            print("⚠️ WARNING: RESEND_API_KEY not set!")

        # Configure sender details
        self.sender_email = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")
        self.sender_name = os.getenv("SENDER_NAME", "E-Commerce App")

    def send_otp_email(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
        """Send OTP via Resend API"""
        try:
            # Verify API key is set
            if not resend.api_key:
                print("❌ ERROR: RESEND_API_KEY not configured")
                return False

            # Determine email subject
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
                                        <h1 style="margin: 0; color: #ffffff; font-size: 28px;">🛍️ E-Commerce</h1>
                                    </td>
                                </tr>
                                
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px;">
                                        <h2 style="margin: 0 0 20px; color: #333333; font-size: 24px;">{title}</h2>
                                        
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
                                        
                                        <p style="margin: 20px 0; color: #666666; font-size: 14px;">
                                            ⏰ <strong>Ce code expire dans 10 minutes.</strong>
                                        </p>
                                        
                                        <p style="margin: 20px 0; color: #999999; font-size: 14px;">
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
                                    </td>
                                </tr>
                                
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """

            # Prepare email parameters (exactly like Resend example)
            email_params = {
                "from": f"{self.sender_name} <{self.sender_email}>",
                "to": recipient_email,  # Can be string or list
                "subject": subject,
                "html": html_content
            }

            print(f"📧 Sending email to {recipient_email} via Resend...")
            print(f"   From: {email_params['from']}")
            print(f"   Subject: {subject}")

            # Send email using Resend (exactly like your example)
            response = resend.Emails.send(email_params)

            print(f"✅ Email sent successfully!")
            print(f"   Email ID: {response.get('id', 'N/A')}")

            return True

        except Exception as e:
            print(f"❌ Error sending email via Resend:")
            print(f"   Type: {type(e).__name__}")
            print(f"   Message: {str(e)}")

            # If it's a Resend-specific error, try to get more details
            if hasattr(e, 'status_code'):
                print(f"   Status Code: {e.status_code}")
            if hasattr(e, 'message'):
                print(f"   API Message: {e.message}")

            return False
