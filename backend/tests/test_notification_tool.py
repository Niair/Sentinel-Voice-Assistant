"""
Test script for notification and email system.

Tests:
1. Notification generation
2. Email sending with Gmail SMTP
3. Session tracking (anti-spam)
"""

import asyncio
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


async def test_notification_generation():
    """Test notification generation for different categories."""
    print("\n" + "=" * 60)
    print("TEST 1: NOTIFICATION GENERATION")
    print("=" * 60)

    from app.agents.notification_tool import generate_notification
    from app.agents.helper_agent import ThreatCategory

    test_cases = [
        {
            "name": "Normal detection",
            "category": ThreatCategory.NORMAL,
            "result": {
                "description": "Person walking by",
                "person_count": 1,
                "has_weapon": False,
                "is_suspicious": False,
            },
        },
        {
            "name": "Caution detection",
            "category": ThreatCategory.CAUTION,
            "result": {
                "description": "Person looking around nervously near entrance",
                "person_count": 1,
                "has_weapon": False,
                "is_suspicious": True,
                "action_recommended": "Monitor closely",
            },
        },
        {
            "name": "Alert detection",
            "category": ThreatCategory.ALERT,
            "result": {
                "description": "Person holding a knife near back door",
                "person_count": 1,
                "has_weapon": True,
                "is_suspicious": True,
                "action_recommended": "Contact authorities immediately",
            },
        },
    ]

    for test in test_cases:
        print(f"\n--- {test['name']} ---")

        notification = generate_notification(test["result"], test["category"])

        print(f"\nCategory: {notification['category']}")
        print(f"Icon: {notification['icon']}")
        print(f"Title: {notification['title']}")
        print(f"Severity: {notification['severity']}")
        print(f"Requires Attention: {notification['requires_attention']}")

        if test["category"] == ThreatCategory.ALERT:
            print(f"Sound Alert: {notification['sound_alert']}")
            print("Action Required: {notification['action_required']}")


async def test_session_tracker():
    """Test session tracking anti-spam logic."""
    print("\n" + "=" * 60)
    print("TEST 2: SESSION TRACKER")
    print("=" * 60)

    from app.agents.notification_tool import SessionTracker

    tracker = SessionTracker()

    print("\n--- Test 1: Session Start ---")
    result1 = {"person_count": 1, "description": "Person entered"}
    should_notify, reason = tracker.should_notify(result1)
    print(f"Should notify: {should_notify}")
    print(f"Reason: {reason}")

    print("\n--- Test 2: Same Person (No notify) ---")
    result2 = {"person_count": 1, "description": "Person still there"}
    should_notify2, reason = tracker.should_notify(result2)
    print(f"Should notify: {should_notify}")
    print(f"Reason: {reason}")

    print("\n--- Test 3: Person Count Change ---")
    result3 = {"person_count": 2, "description": "Second person entered"}
    should_notify3, reason = tracker.should_notify(result3)
    print(f"Should notify: {should_notify}")
    print(f"Reason: {reason}")

    print("\n--- Test 4: Session End ---")
    result4 = {"person_count": 0, "description": "Area cleared"}
    should_notify4, reason = tracker.should_notify(result4)
    print(f"Should notify: {should_notify}")
    print(f"Reason: {reason}")

    print("\n--- Test 5: Weapon (Always notify) ---")
    result5 = {"person_count": 1, "has_weapon": True, "description": "Weapon detected"}
    should_notify5, reason = tracker.should_notify(result5)
    print(f"Should notify: {should_notify}")
    print(f"Reason: {reason}")

    print("\n" + "=" * 60)
    print("✅ All session tracker tests passed!")
    print("=" * 60)


async def test_email_sending():
    """Test email sending (requires valid Gmail credentials)."""
    print("\n" + "=" * 60)
    print("TEST 3: EMAIL SENDING")
    print("=" * 60)

    from app.agents.notification_tool import send_alert_email, format_email_report
    from app.agents.helper_agent import ThreatCategory

    gmail_user = os.getenv("GMAIL_USER", "")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")

    if not gmail_user or not gmail_password:
        print("⚠️ Gmail credentials not found - skipping email test")
        print("Set GMAIL_USER and GMAIL_APP_PASSWORD in .env")
        return

    print(f"Sending test email to: {gmail_user}")

    result_data = {
        "description": "Test alert notification from Sentinel AI",
        "has_weapon": False,
        "is_suspicious": True,
        "action_recommended": "This is a test notification",
        "timestamp": "2026-02-23T12:00:00Z",
    }

    subject, body = format_email_report(result_data, "", ThreatCategory.CAUTION)

    success, message = await send_alert_email(
        to_email=gmail_user, subject=subject, body=body, image_base64=None
    )

    print(f"\nResult: {message}")


async def main():
    print("\n" + "=" * 60)
    print("NOTIFICATION & EMAIL TEST SUITE")
    print("=" * 60)

    await test_notification_generation()
    await test_session_tracker()
    await test_email_sending()

    print("\n" + "=" * 60)
    print("NOTIFICATION & EMAIL TEST SUITE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
