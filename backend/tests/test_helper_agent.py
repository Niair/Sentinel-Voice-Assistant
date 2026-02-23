"""
Test script for Helper Agent.

Tests:
1. Deduplication functionality
2. Emotion analysis
3. Verification and formatting
4. Threat categorization
"""

import asyncio
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


async def test_deduplication():
    """Test the duplicate removal functionality."""
    print("\n" + "=" * 60)
    print("TEST 1: DEDUPLICATION")
    print("=" * 60)

    from app.agents.helper_agent import get_helper_agent

    helper = get_helper_agent()

    test_cases = [
        {
            "name": "Duplicate paragraph",
            "input": """**Mood:** Contemplative
**Signs:** Head tilted upwards, eyes gazing upwards
**Energy:** Low
You seem to be in a contemplative mood, with a low energy level.
**Mood:** Contemplative
**Signs:** Head tilted upwards, eyes gazing upwards
**Energy:** Low
You seem to be in a contemplative mood, with a low energy level.""",
        },
        {
            "name": "Duplicate sentences",
            "input": """The person is wearing a gray sweater. The person is wearing a gray sweater.
They appear to be sitting in a chair. They appear to be sitting in a chair.""",
        },
        {
            "name": "Clean text (no duplicates)",
            "input": """**Appearance:** Wearing a blue casual shirt with dark jeans.
**Mood:** Happy and relaxed
**Activity:** Sitting at a desk
You look great today!""",
        },
    ]

    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        print(f"Input ({len(test['input'])} chars):")
        print(
            test["input"][:200] + "..." if len(test["input"]) > 200 else test["input"]
        )

        cleaned = helper._clean_duplicates(test["input"])

        print(f"\nOutput ({len(cleaned)} chars):")
        print(cleaned)

        if len(cleaned) < len(test["input"]):
            reduction = (1 - len(cleaned) / len(test["input"])) * 100
            print(f"✅ Reduced by {reduction:.1f}%")
        else:
            print("ℹ️ No reduction (input was clean)")


async def test_emotion_analysis():
    """Test emotion analysis functionality."""
    print("\n" + "=" * 60)
    print("TEST 2: EMOTION ANALYSIS")
    print("=" * 60)

    from app.agents.helper_agent import get_helper_agent

    helper = get_helper_agent()

    print("\nNote: This test uses text-only analysis (no image).")
    print("In production, it will use Qwen 3.5 vision capabilities.")

    context = "Person is smiling and appears relaxed"

    try:
        result = await helper.analyze_emotions(image_base64="", context=context)

        print(f"\nSuccess: {result.get('success')}")
        print(f"Primary Emotion: {result.get('primary_emotion')}")
        print(f"\nAnalysis:")
        print(result.get("emotion_analysis", "No analysis"))

    except Exception as e:
        print(f"❌ Error: {e}")


async def test_verify_and_format():
    """Test verification and formatting."""
    print("\n" + "=" * 60)
    print("TEST 3: VERIFY AND FORMAT")
    print("=" * 60)

    from app.agents.helper_agent import get_helper_agent, QueryType

    helper = get_helper_agent()

    test_cases = [
        {
            "name": "Appearance query with duplicates",
            "query_type": QueryType.APPEARANCE,
            "raw_output": """The person in this image is wearing a gray and black sweater with a red stripe.
They have short black hair. They appear to be looking up at something.
The person in this image is wearing a gray and black sweater with a red stripe.
They have short black hair. They appear to be looking up at something.
You look nice and comfortable!""",
        },
        {
            "name": "Emotion query",
            "query_type": QueryType.EMOTION,
            "raw_output": """**Mood:** Contemplative
**Signs:** Head tilted upwards
**Energy:** Low
**Mood:** Contemplative
**Signs:** Head tilted upwards
**Energy:** Low""",
        },
    ]

    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        print(f"Query Type: {test['query_type'].value}")
        print(f"Raw Output: {test['raw_output'][:100]}...")

        try:
            result = await helper.verify_and_format(
                raw_output=test["raw_output"],
                image_base64="",
                query_type=test["query_type"],
            )

            print(f"\nSuccess: {result.get('success')}")
            print(f"\nFormatted Response:")
            print(result.get("formatted_response"))

        except Exception as e:
            print(f"❌ Error: {e}")


async def test_threat_categorization():
    """Test threat categorization."""
    print("\n" + "=" * 60)
    print("TEST 4: THREAT CATEGORIZATION")
    print("=" * 60)

    from app.agents.helper_agent import get_helper_agent, ThreatCategory

    helper = get_helper_agent()

    test_cases = [
        {
            "name": "Normal detection",
            "result": {
                "person_count": 1,
                "has_weapon": False,
                "is_suspicious": False,
                "description": "Person walking by",
            },
            "expected": ThreatCategory.NORMAL,
        },
        {
            "name": "Suspicious activity",
            "result": {
                "person_count": 1,
                "has_weapon": False,
                "is_suspicious": True,
                "description": "Person looking around nervously",
            },
            "expected": ThreatCategory.CAUTION,
        },
        {
            "name": "Weapon detected",
            "result": {
                "person_count": 1,
                "has_weapon": True,
                "is_suspicious": True,
                "description": "Person holding a knife",
            },
            "expected": ThreatCategory.ALERT,
        },
        {
            "name": "High threat level",
            "result": {"threat_level": "high", "description": "Break-in attempt"},
            "expected": ThreatCategory.ALERT,
        },
    ]

    all_passed = True

    for test in test_cases:
        category = helper.categorize_threat(test["result"])
        passed = category == test["expected"]

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status} - {test['name']}")
        print(f"  Input: {test['result']}")
        print(f"  Expected: {test['expected'].value}")
        print(f"  Got: {category.value}")

        if not passed:
            all_passed = False

    print(f"\n{'=' * 60}")
    if all_passed:
        print("✅ All threat categorization tests passed!")
    else:
        print("❌ Some tests failed")


async def test_email_decision():
    """Test email sending decision logic."""
    print("\n" + "=" * 60)
    print("TEST 5: EMAIL DECISION")
    print("=" * 60)

    from app.agents.helper_agent import get_helper_agent, ThreatCategory

    helper = get_helper_agent()

    test_cases = [
        {
            "category": ThreatCategory.NORMAL,
            "details": {"verified": True},
            "expected": False,
        },
        {
            "category": ThreatCategory.CAUTION,
            "details": {"is_suspicious": True, "verified": True},
            "expected": True,
        },
        {
            "category": ThreatCategory.CAUTION,
            "details": {"is_suspicious": False, "verified": True},
            "expected": False,
        },
        {
            "category": ThreatCategory.ALERT,
            "details": {"verified": True},
            "expected": True,
        },
    ]

    all_passed = True

    for test in test_cases:
        should_send = helper.should_send_email(test["category"], test["details"])
        passed = should_send == test["expected"]

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status} - {test['category'].value}")
        print(f"  Details: {test['details']}")
        print(f"  Expected email: {test['expected']}")
        print(f"  Got: {should_send}")

        if not passed:
            all_passed = False

    print(f"\n{'=' * 60}")
    if all_passed:
        print("✅ All email decision tests passed!")
    else:
        print("❌ Some tests failed")


async def test_ollama_connection():
    """Test connection to Ollama Cloud API."""
    print("\n" + "=" * 60)
    print("TEST 6: OLLAMA API CONNECTION")
    print("=" * 60)

    try:
        from langchain_ollama import OllamaLLM

        llm = OllamaLLM(model="qwen3.5:cloud")

        print("\nSending test request to Ollama Cloud (qwen3.5:cloud)...")

        response = llm.invoke("Say 'Hello from Helper Agent!' in one sentence.")

        print(f"✅ Connection successful!")
        print(f"Response: {response}")

    except Exception as e:
        print(f"❌ Connection failed: {e}")


async def main():
    print("=" * 60)
    print("HELPER AGENT TEST SUITE")
    print("=" * 60)

    await test_deduplication()
    await test_threat_categorization()
    await test_email_decision()
    await test_ollama_connection()
    await test_verify_and_format()
    await test_emotion_analysis()

    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
