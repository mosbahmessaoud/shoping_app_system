from sqlalchemy.orm import Session
from models.notification import Notification
from models.bill import Bill
from models.client import Client
from models.admin import Admin
from models.stock_alert import StockAlert
from models.product import Product
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from typing import Optional

# Configuration Email (à modifier selon votre fournisseur)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "votre_email@gmail.com"  # Changez ceci
SMTP_PASSWORD = "votre_mot_de_passe"      # Changez ceci
FROM_EMAIL = "votre_email@gmail.com"       # Changez ceci

# Configuration WhatsApp API (exemple avec Twilio)
WHATSAPP_API_URL = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
TWILIO_ACCOUNT_SID = "votre_account_sid"   # Changez ceci
TWILIO_AUTH_TOKEN = "votre_auth_token"     # Changez ceci
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Numéro Twilio WhatsApp

def create_bill_notification(db: Session, bill: Bill, client: Client) -> list:
    """
    Créer des notifications pour une nouvelle facture
    
    Args:
        db: Session de base de données
        bill: Facture créée
        client: Client qui a créé la facture
        
    Returns:
        Liste des notifications créées
    """
    
    notifications = []
    
    # Obtenir tous les admins
    admins = db.query(Admin).all()
    
    # Message pour l'admin
    admin_message = f"""
Nouvelle facture créée!

Facture N°: {bill.bill_number}
Client: {client.username} ({client.email})
Téléphone: {client.phone_number or 'Non fourni'}
Ville: {client.city or 'Non fournie'}

Montant total: {bill.total_amount} DZD
Statut: {bill.status}

Détails de la facture:
"""
    
    # Ajouter les items de la facture
    for item in bill.bill_items:
        admin_message += f"\n- {item.product_name}: {item.quantity} x {item.unit_price} DZD = {item.subtotal} DZD"
    
    # Créer une notification pour chaque admin (email et WhatsApp)
    for admin in admins:
        # Notification par email
        if admin.email:
            email_notification = Notification(
                admin_id=admin.id,
                client_id=client.id,
                bill_id=bill.id,
                notification_type="new_bill",
                channel="email",
                message=admin_message
            )
            db.add(email_notification)
            notifications.append(email_notification)
        
        # Notification par WhatsApp
        if admin.phone_number:
            whatsapp_notification = Notification(
                admin_id=admin.id,
                client_id=client.id,
                bill_id=bill.id,
                notification_type="new_bill",
                channel="whatsapp",
                message=admin_message
            )
            db.add(whatsapp_notification)
            notifications.append(whatsapp_notification)
    
    # Message pour le client
    client_message = f"""
Votre facture a été créée avec succès!

Facture N°: {bill.bill_number}
Date: {bill.created_at.strftime('%d/%m/%Y %H:%M')}

Montant total: {bill.total_amount} DZD
Montant payé: {bill.total_paid} DZD
Montant restant: {bill.total_remaining} DZD

Merci pour votre achat!
"""
    
    # Notification email pour le client
    if client.email:
        client_email_notification = Notification(
            client_id=client.id,
            bill_id=bill.id,
            notification_type="bill_confirmation",
            channel="email",
            message=client_message
        )
        db.add(client_email_notification)
        notifications.append(client_email_notification)
    
    db.commit()
    
    return notifications

def create_stock_alert_notification(db: Session, alert: StockAlert, product: Product) -> list:
    """
    Créer des notifications pour une alerte de stock
    
    Args:
        db: Session de base de données
        alert: Alerte de stock créée
        product: Produit concerné
        
    Returns:
        Liste des notifications créées
    """
    
    notifications = []
    
    # Obtenir tous les admins
    admins = db.query(Admin).all()
    
    # Déterminer la priorité
    priority = "🔴 URGENT" if alert.alert_type == "out_of_stock" else "⚠️ ATTENTION"
    
    # Message pour l'admin
    message = f"""
{priority} - Alerte de stock!

Produit: {product.name}
Catégorie: {product.category.name}
Stock actuel: {product.quantity_in_stock} unités
Stock minimum: {product.minimum_stock_level} unités

Type d'alerte: {alert.alert_type}
Message: {alert.message}

Action requise: Réapprovisionner le stock dès que possible.
"""
    
    # Créer une notification pour chaque admin
    for admin in admins:
        # Notification par email
        if admin.email:
            email_notification = Notification(
                admin_id=admin.id,
                stock_alert_id=alert.id,
                notification_type="stock_alert",
                channel="email",
                message=message
            )
            db.add(email_notification)
            notifications.append(email_notification)
        
        # Notification par WhatsApp (pour les alertes critiques)
        if admin.phone_number and alert.alert_type == "out_of_stock":
            whatsapp_notification = Notification(
                admin_id=admin.id,
                stock_alert_id=alert.id,
                notification_type="stock_alert",
                channel="whatsapp",
                message=message
            )
            db.add(whatsapp_notification)
            notifications.append(whatsapp_notification)
    
    db.commit()
    
    return notifications

def create_payment_notification(db: Session, payment, bill: Bill, client: Client, admin: Admin) -> list:
    """
    Créer des notifications pour un nouveau paiement
    
    Args:
        db: Session de base de données
        payment: Paiement créé
        bill: Facture concernée
        client: Client qui paye
        admin: Admin qui enregistre le paiement
        
    Returns:
        Liste des notifications créées
    """
    
    notifications = []
    
    # Message pour le client
    client_message = f"""
Paiement enregistré!

Facture N°: {bill.bill_number}
Montant payé: {payment.amount_paid} DZD
Date de paiement: {payment.payment_date.strftime('%d/%m/%Y')}
Méthode: {payment.payment_method or 'Non spécifiée'}

Résumé de la facture:
- Montant total: {bill.total_amount} DZD
- Total payé: {bill.total_paid} DZD
- Montant restant: {bill.total_remaining} DZD

Statut: {bill.status}

Merci pour votre paiement!
"""
    
    # Notification pour le client
    if client.email:
        client_notification = Notification(
            client_id=client.id,
            bill_id=bill.id,
            notification_type="payment_received",
            channel="email",
            message=client_message
        )
        db.add(client_notification)
        notifications.append(client_notification)
    
    db.commit()
    
    return notifications

def send_email_notification(to_email: str, subject: str, message: str) -> bool:
    """
    Envoyer une notification par email
    
    Args:
        to_email: Email du destinataire
        subject: Sujet de l'email
        message: Corps du message
        
    Returns:
        True si envoyé avec succès, False sinon
    """
    
    try:
        # Créer le message
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Ajouter le corps du message
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        # Se connecter au serveur SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        # Envoyer l'email
        text = msg.as_string()
        server.sendmail(FROM_EMAIL, to_email, text)
        server.quit()
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {str(e)}")
        return False

def send_whatsapp_notification(to_phone: str, message: str) -> bool:
    """
    Envoyer une notification par WhatsApp (via Twilio)
    
    Args:
        to_phone: Numéro de téléphone du destinataire (format: +213XXXXXXXXX)
        message: Message à envoyer
        
    Returns:
        True si envoyé avec succès, False sinon
    """
    
    try:
        # Formater le numéro pour WhatsApp
        if not to_phone.startswith('whatsapp:'):
            to_phone = f"whatsapp:{to_phone}"
        
        # Préparer la requête
        url = WHATSAPP_API_URL.format(account_sid=TWILIO_ACCOUNT_SID)
        
        data = {
            'From': TWILIO_WHATSAPP_NUMBER,
            'To': to_phone,
            'Body': message
        }
        
        # Envoyer la requête
        response = requests.post(
            url,
            data=data,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        )
        
        return response.status_code == 201
        
    except Exception as e:
        print(f"Erreur lors de l'envoi du message WhatsApp: {str(e)}")
        return False

def send_pending_notifications(db: Session) -> dict:
    """
    Envoyer toutes les notifications en attente
    
    Args:
        db: Session de base de données
        
    Returns:
        dict avec les statistiques d'envoi
    """
    
    from datetime import datetime
    
    # Récupérer les notifications en attente
    pending_notifications = db.query(Notification).filter(
        Notification.is_sent == False
    ).all()
    
    sent_count = 0
    failed_count = 0
    
    for notification in pending_notifications:
        success = False
        
        # Déterminer le destinataire
        if notification.admin_id:
            recipient = db.query(Admin).filter(Admin.id == notification.admin_id).first()
        elif notification.client_id:
            recipient = db.query(Client).filter(Client.id == notification.client_id).first()
        else:
            continue
        
        # Envoyer selon le canal
        if notification.channel == "email" and recipient.email:
            subject = f"Notification - {notification.notification_type}"
            success = send_email_notification(recipient.email, subject, notification.message)
            
        elif notification.channel == "whatsapp" and recipient.phone_number:
            success = send_whatsapp_notification(recipient.phone_number, notification.message)
        
        # Mettre à jour le statut
        if success:
            notification.is_sent = True
            notification.sent_at = datetime.now()
            sent_count += 1
        else:
            failed_count += 1
    
    db.commit()
    
    return {
        "total": len(pending_notifications),
        "sent": sent_count,
        "failed": failed_count
    }