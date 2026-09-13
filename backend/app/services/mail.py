import smtplib
from email.message import EmailMessage
from app.core.config import settings

def send_reset(recipient, token):
    message=EmailMessage()
    message['Subject']='Reset your FraudMesh password'
    message['From']=settings.smtp_sender
    message['To']=recipient
    message.set_content(f'Use this one-time link within 15 minutes to reset your password:\n{settings.frontend_url.rstrip("/")}/reset-password?token={token}\n\nIf you did not request this, ignore this message.')
    with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_username: smtp.login(settings.smtp_username,settings.smtp_password or '')
        smtp.send_message(message)
