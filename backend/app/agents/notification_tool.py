"""
Notification and Email System for Security Alerts.

Features:
- Smart notification generation based on threat category
- Gmail SMTP integration for email alerts
- Image attachment support
- Anti-spam session tracking

Categories:
- NORMAL (👤): Background log only
- CAUTION (⚠️): User notification via WebSocket
- ALERT (🚨): Email notification + Main Agent interrupt
"""

import os
import smtplib
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List

from app.agents.helper_agent import ThreatCategory

logger = logging.getLogger(__name__)

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
USER_ALERT_EMAIL = os.getenv("USER_ALERT_EMAIL", GMAIL_USER)


NOTIFICATION_TEMPLATES = {
    ThreatCategory.NORMAL: {
        "icon": "👤",
        "title": "Person Detected",
        "severity": "LOW",
        "color": "#4CAF50",
    },
    ThreatCategory.CAUTION: {
        "icon": "⚠️",
        "title": "Suspicious Activity",
        "severity": "MEDIUM",
        "color": "#FF9800",
    },
    ThreatCategory.ALERT: {
        "icon": "🚨",
        "title": "THREAT DETECTED",
        "severity": "HIGH",
        "color": "#F44336",
    },
}


def generate_notification(
    result: Dict[str, Any], category: ThreatCategory
) -> Dict[str, Any]:
    """
    Generate notification dict based on threat category.

    Args:
        result: Detection result from Helper Agent
        category: ThreatCategory (NORMAL/CAUTION/ALERT)

    Returns:
        Dict with notification details for WebSocket broadcast
    """
    template = NOTIFICATION_TEMPLATES.get(
        category, NOTIFICATION_TEMPLATES[ThreatCategory.NORMAL]
    )

    description = result.get("description", "Activity detected")
    person_count = result.get("person_count", 0)
    timestamp = result.get("timestamp", datetime.utcnow().isoformat())

    fields = {}

    if person_count > 0:
        fields["People Detected"] = f"{person_count} person(s)"

    if result.get("has_weapon"):
        fields["Weapon Detected"] = "YES - TAKE ACTION"

    if result.get("is_suspicious"):
        fields["Suspicious Activity"] = "Yes"

    if result.get("action_recommended"):
        fields["Recommended Action"] = result["action_recommended"]

    notification = {
        "type": "security_notification",
        "category": category.value,
        "icon": template["icon"],
        "title": template["title"],
        "severity": template["severity"],
        "color": template["color"],
        "description": description,
        "fields": fields,
        "timestamp": timestamp,
        "requires_attention": category != ThreatCategory.NORMAL,
    }

    if category == ThreatCategory.ALERT:
        notification["action_required"] = (
            "Review immediately and take appropriate action"
        )
        notification["sound_alert"] = True

    return notification


async def send_alert_email(
    to_email: str, subject: str, body: str, image_base64: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Send alert email with optional image attachment via Gmail SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (HTML supported)
        image_base64: Optional base64-encoded image to attach

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logger.error("❌ Gmail credentials not configured")
        return False, "Gmail credentials not configured"

    if not to_email:
        logger.error("❌ No recipient email provided")
        return False, "No recipient email provided"

    try:
        msg = MIMEMultipart("related")
        msg["From"] = GMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #dc3545; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px; }}
                .alert-box {{ background: #fff; border-left: 4px solid #dc3545; padding: 15px; margin: 15px 0; }}
                .timestamp {{ color: #666; font-size: 0.9em; }}
                .image-container {{ margin: 20px 0; text-align: center; }}
                .image-container img {{ max-width: 100%; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.8em; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Sentinel Security Alert</h1>
                </div>
                <div class="content">
                    {body}
                </div>
                <div class="footer">
                    <p>This is an automated security alert from Sentinel AI.</p>
                    <p>Generated at: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        if image_base64:
            try:
                image_data = base64.b64decode(image_base64)
                image = MIMEImage(image_data)
                image.add_header("Content-ID", "<security_image>")
                image.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename="security_evidence.jpg",
                )
                msg.attach(image)

                image_html = """
                <div class="image-container">
                    <h3>📷 Security Camera Evidence</h3>
                    <img src="cid:security_image" alt="Security Camera Image" />
                </div>
                """
                html_body = html_body.replace("{body}", body + image_html)
                msg.attach(MIMEText(html_body, "html"))

            except Exception as img_error:
                logger.warning(f"⚠️ Failed to attach image: {img_error}")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())

        logger.info(f"✅ Alert email sent to {to_email}")
        return True, f"Email sent successfully to {to_email}"

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail authentication failed - check credentials")
        return False, "Gmail authentication failed - check credentials"

    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP error: {e}")
        return False, f"SMTP error: {str(e)}"

    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False, f"Failed to send email: {str(e)}"


def format_email_report(
    result: Dict[str, Any], image_base64: str, category: ThreatCategory
) -> Tuple[str, str]:
    """
    Format email subject and HTML body for security alert.

    Args:
        result: Detection result from Helper Agent
        image_base64: Base64-encoded security camera image
        category: ThreatCategory

    Returns:
        Tuple of (subject, html_body)
    """
    template = NOTIFICATION_TEMPLATES.get(
        category, NOTIFICATION_TEMPLATES[ThreatCategory.NORMAL]
    )

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    subject = f"{template['icon']} Sentinel Alert: {template['title']} - {timestamp}"

    body_parts = [
        f"<div class='alert-box'>",
        f"<h2>{template['icon']} {template['title']}</h2>",
        f"<p class='timestamp'>Detected at: {timestamp}</p>",
        f"</div>",
    ]

    if result.get("description"):
        body_parts.append(
            f"<p><strong>Description:</strong> {result['description']}</p>"
        )

    if result.get("person_count"):
        body_parts.append(
            f"<p><strong>People Detected:</strong> {result['person_count']}</p>"
        )

    if result.get("has_weapon"):
        body_parts.append(
            f"<p><strong>⚠️ WEAPON DETECTED:</strong> Yes - Immediate action required</p>"
        )

    if result.get("is_suspicious"):
        body_parts.append(f"<p><strong>Suspicious Activity:</strong> Yes</p>")

    if result.get("action_recommended"):
        body_parts.append(f"<div class='alert-box'>")
        body_parts.append(f"<h3>Recommended Action:</h3>")
        body_parts.append(f"<p>{result['action_recommended']}</p>")
        body_parts.append(f"</div>")

    body = "".join(body_parts)

    if image_base64:
        body += """
        <div class="image-container">
            <h3>📷 Security Camera Evidence</h3>
            <img src="cid:security_image" alt="Security Camera Image" style="max-width: 100%; border-radius: 8px;" />
        </div>
        """

    return subject, body


class SessionTracker:
    """
    Enhanced session tracking to prevent notification spam.

    Tracks:
    - Active monitoring sessions
    - Person count changes
    - Activity changes
    - Last notification times

    Prevents:
    - Repeated notifications for same person
    - Spam when person stays in frame
    """

    def __init__(self, notification_gap: int = 300):
        """
        Initialize session tracker.

        Args:
            notification_gap: Minimum seconds between notifications (default: 5 minutes)
        """
        self.session_active = False
        self.last_person_count = 0
        self.last_activity = ""
        self.session_start_time: Optional[datetime] = None
        self.last_notification_time: Optional[datetime] = None
        self.notification_gap = notification_gap

        self.activity_history: List[str] = []
        self.max_history = 10

    def should_notify(self, current_result: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Decide if notification should be sent based on anti-spam rules.

        Args:
            current_result: Current detection result

        Returns:
            Tuple of (should_notify: bool, reason: str)
        """
        now = datetime.utcnow()

        person_count = current_result.get("person_count", 0)
        activity = current_result.get("description", "")

        if current_result.get("has_weapon"):
            return True, "WEAPON_DETECTED"

        if (
            current_result.get("is_suspicious")
            and current_result.get("category") == "alert"
        ):
            return True, "HIGH_THREAT"

        if person_count == 0 and self.session_active:
            self.session_active = False
            duration = (
                (now - self.session_start_time).total_seconds()
                if self.session_start_time
                else 0
            )
            self.session_start_time = None
            return True, f"SESSION_END (duration: {duration:.0f}s)"

        if person_count > 0 and not self.session_active:
            self.session_active = True
            self.session_start_time = now
            self.last_person_count = person_count
            self.last_activity = activity
            return True, "SESSION_START"

        if person_count != self.last_person_count:
            old_count = self.last_person_count
            self.last_person_count = person_count
            return True, f"COUNT_CHANGE ({old_count} -> {person_count})"

        if activity != self.last_activity and len(activity) > 10:
            old_activity = self.last_activity
            self.last_activity = activity
            self.activity_history.append(activity)
            if len(self.activity_history) > self.max_history:
                self.activity_history.pop(0)
            return True, "ACTIVITY_CHANGE"

        return False, "NO_CHANGE"

    def record_notification(self):
        """Record that a notification was sent."""
        self.last_notification_time = datetime.utcnow()

    def reset(self):
        """Reset session state."""
        self.session_active = False
        self.last_person_count = 0
        self.last_activity = ""
        self.session_start_time = None
        self.last_notification_time = None
        self.activity_history = []


_session_tracker: Optional[SessionTracker] = None


def get_session_tracker() -> SessionTracker:
    """Get or create session tracker singleton."""
    global _session_tracker
    if _session_tracker is None:
        _session_tracker = SessionTracker()
    return _session_tracker
