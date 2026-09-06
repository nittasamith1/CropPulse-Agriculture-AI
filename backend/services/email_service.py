"""
CropPulse – Email Service
Asynchronously sends account verification and password reset emails using aiosmtplib.
Gracefully handles SMTP credentials unavailability by logging link info to stdout/stderr.
"""

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from loguru import logger
from backend.config import settings

class EmailService:
    """Manages transactional emails using SMTP or logs fallback link info."""

    async def _send_smtp_email(self, recipient: str, subject: str, body_html: str, body_text: str):
        """Helper to send email via SMTP asynchronously."""
        if not settings.EMAIL_ENABLED or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning(f"📧 SMTP email sending is disabled. Skipping delivery to: {recipient}")
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
        message["To"] = recipient

        # Attach text and html versions
        message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(body_html, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_PORT == 465,
                start_tls=settings.SMTP_PORT == 587
            )
            logger.info(f"📧 Email successfully sent to: {recipient}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send SMTP email to {recipient}: {e}")
            return False

    async def send_verification_email(self, email: str, token: str):
        """Send account verification/activation email."""
        link = f"{settings.FRONTEND_URL}/pages/login.html?verify_token={token}"
        subject = "🌱 Verify Your CropPulse Account"
        
        body_text = f"Welcome to CropPulse!\n\nPlease activate your account by visiting the link: {link}"
        body_html = f"""
        <html>
            <body>
                <h2 style="color: #2E7D32;">🌱 Welcome to CropPulse!</h2>
                <p>Thank you for signing up. Please click the button below to verify your email and activate your account:</p>
                <p style="margin: 20px 0;">
                    <a href="{link}" style="background-color: #2E7D32; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Verify Email</a>
                </p>
                <p>Or copy this link: <a href="{link}">{link}</a></p>
            </body>
        </html>
        """
        
        logger.info(f"🔑 [Verification Token] Email: {email} | Token: {token} | Link: {link}")
        await self._send_smtp_email(email, subject, body_html, body_text)

    async def send_password_reset_email(self, email: str, token: str):
        """Send password reset email."""
        link = f"{settings.FRONTEND_URL}/pages/reset-password.html?token={token}"
        subject = "🔑 Reset Your CropPulse Password"
        
        body_text = f"Reset your CropPulse password.\n\nPlease reset your password by visiting the link: {link}"
        body_html = f"""
        <html>
            <body>
                <h2 style="color: #2E7D32;">🔑 CropPulse Password Reset</h2>
                <p>You requested a password reset for your account. Click the button below to set a new password:</p>
                <p style="margin: 20px 0;">
                    <a href="{link}" style="background-color: #2E7D32; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
                </p>
                <p>This link will expire in 1 hour.</p>
                <p>Or copy this link: <a href="{link}">{link}</a></p>
                <p style="color: #777; font-size: 0.85em;">If you did not request this, please ignore this email.</p>
            </body>
        </html>
        """
        
        logger.info(f"🔑 [Password Reset Token] Email: {email} | Token: {token} | Link: {link}")
        await self._send_smtp_email(email, subject, body_html, body_text)

email_service = EmailService()
