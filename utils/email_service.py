# utils/email_service.py
import os
import resend

class EmailService:
    def __init__(self):
        # Set API key from environment
        resend.api_key = os.getenv("RESEND_API_KEY")
        # Use default Resend sender (no domain needed!)
        self.sender_email = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")
        self.sender_name = os.getenv("SENDER_NAME", "Votre Application")
        
    def send_otp_email(self, recipient_email: str, otp_code: str, otp_type: str) -> bool:
        """Send OTP via Resend"""
        try:
            # Validate configuration
            if not resend.api_key:
                print("ERROR: RESEND_API_KEY not configured")
                return False
            
            subject = "Code de vérification" if otp_type == "registration" else "Réinitialisation du mot de passe"
            
            html_body = f"""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.6; 
                        color: #333;
                        margin: 0;
                        padding: 0;
                        background-color: #f5f5f5;
                    }}
                    .email-container {{ 
                        max-width: 600px; 
                        margin: 40px auto; 
                        background: white;
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 40px 20px;
                        text-align: center;
                        color: white;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 24px;
                        font-weight: 600;
                    }}
                    .content {{ 
                        padding: 40px 30px;
                    }}
                    .otp-box {{ 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 30px; 
                        text-align: center; 
                        border-radius: 12px;
                        margin: 30px 0;
                        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                    }}
                    .otp-code {{ 
                        color: white; 
                        font-size: 48px; 
                        font-weight: bold;
                        letter-spacing: 12px;
                        margin: 0;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
                        font-family: 'Courier New', monospace;
                    }}
                    .info-box {{ 
                        background: #fff3cd; 
                        padding: 20px; 
                        border-left: 4px solid #ffc107;
                        border-radius: 4px;
                        margin: 25px 0;
                    }}
                    .info-box p {{
                        margin: 0;
                        color: #856404;
                    }}
                    .footer {{
                        background: #f8f9fa;
                        padding: 20px 30px;
                        text-align: center;
                        color: #666;
                        font-size: 13px;
                        border-top: 1px solid #e9ecef;
                    }}
                    .emoji {{
                        font-size: 24px;
                        margin-right: 8px;
                    }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="header">
                        <h1><span class="emoji">{'🔐' if otp_type == 'registration' else '🔑'}</span>
                        {'Vérification de votre compte' if otp_type == 'registration' else 'Réinitialisation de mot de passe'}</h1>
                    </div>
                    
                    <div class="content">
                        <p style="font-size: 16px; color: #555;">
                            {'Bienvenue ! Pour finaliser votre inscription, veuillez utiliser le code ci-dessous :' if otp_type == 'registration' else 'Vous avez demandé à réinitialiser votre mot de passe. Utilisez le code ci-dessous :'}
                        </p>
                        
                        <div class="otp-box">
                            <p class="otp-code">{otp_code}</p>
                        </div>
                        
                        <div class="info-box">
                            <p><strong>⏱️ Important :</strong> Ce code expire dans <strong>10 minutes</strong>.</p>
                        </div>
                        
                        <p style="color: #666; font-size: 14px; margin-top: 30px;">
                            Si vous n'avez pas demandé ce code, vous pouvez ignorer cet email en toute sécurité.
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p>Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
                        <p style="margin-top: 10px;">© 2024 {self.sender_name}. Tous droits réservés.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version (fallback)
            text_body = f"""
            {'Vérification de votre compte' if otp_type == 'registration' else 'Réinitialisation de mot de passe'}
            
            Votre code de vérification est: {otp_code}
            
            Ce code expire dans 10 minutes.
            
            Si vous n'avez pas demandé ce code, veuillez ignorer cet email.
            """
            
            params = {
                "from": f"{self.sender_name} <{self.sender_email}>",
                "to": [recipient_email],
                "subject": subject,
                "html": html_body,
                "text": text_body,
            }
            
            email = resend.Emails.send(params)
            print(f"✅ Email sent successfully to {recipient_email}")
            print(f"   Email ID: {email['id']}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email: {type(e).__name__}: {str(e)}")
            return False