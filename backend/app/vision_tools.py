"""
Vision Tools using Google Gemini for intelligent image analysis.
Provides scene understanding, threat detection, and fashion advice.
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_vision_model = None


def _get_vision_client():
    """Lazy load Gemini Vision client using new google-genai SDK."""
    global _vision_model
    if _vision_model is None:
        try:
            from google import genai

            _vision_model = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("✅ Gemini Vision client initialized with google-genai")
        except ImportError:
            logger.error(
                "❌ google-genai package not installed. Run: uv pip install google-genai"
            )
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini Vision: {e}")
            raise
    return _vision_model


# Alias for backward compatibility
_get_vision_model = _get_vision_client


def _generate_content_with_image(client, image_data: bytes, prompt: str) -> str:
    """Generate content using the new Google GenAI SDK."""
    from google.genai import types

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
                    types.Part.from_text(text=prompt),
                ],
            )
        ],
    )
    return response.text


def _is_quota_exceeded(error_message: str) -> bool:
    """Check if error is due to quota exceeded."""
    quota_keywords = ["quota", "429", "exceeded", "rate limit"]
    return any(keyword in error_message.lower() for keyword in quota_keywords)


def _handle_vision_error(error: Exception, tool_name: str) -> str:
    """Handle vision tool errors gracefully."""
    error_str = str(error)

    if _is_quota_exceeded(error_str):
        logger.warning(f"⚠️ Gemini quota exceeded in {tool_name}")
        return "⚠️ Vision service temporarily unavailable (quota exceeded). Please try again later."

    logger.error(f"❌ {tool_name} error: {error}")
    return f"❌ Vision analysis failed: {error_str}"


def _encode_frame_to_base64(frame) -> str:
    """Convert OpenCV frame to base64 string."""
    import cv2

    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode("utf-8")


@tool
async def analyze_frame_for_threats(frame_base64: str = None, frame=None) -> str:
    """
    Analyze a camera frame for security threats including weapons and suspicious objects.

    IMPORTANT: Only use this tool when user EXPLICITLY asks about security threats, weapons,
    or danger. Do NOT use for casual conversation.

    Use this when:
    - User EXPLICITLY asks: "Is it safe?", "Check for threats", "Any weapons?"
    - User asks about security or dangerous situations

    Args:
        frame_base64: Base64 encoded image (optional)
        frame: OpenCV frame directly (optional)

    Returns:
        Threat assessment with severity level and description.
    """
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not configured. Set GEMINI_API_KEY in .env"

    try:
        if frame is not None and frame_base64 is None:
            frame_base64 = _encode_frame_to_base64(frame)

        if not frame_base64:
            return "❌ No frame provided for analysis"

        model = _get_vision_model()

        prompt = """Analyze this security camera image for potential threats.

Look for:
1. WEAPONS: knives, guns, baseball bats, sharp objects, blunt weapons
2. THREATENING BEHAVIOR: aggressive postures, raised fists, chasing
3. SUSPICIOUS OBJECTS: masks, gloves (worn by non-workers), crowbars, pry tools
4. MULTIPLE PEOPLE: count how many people and note their positions

Respond in this exact JSON format:
{
    "threat_detected": true/false,
    "threat_type": "weapon" | "behavior" | "suspicious_object" | "crowd" | "none",
    "severity": "high" | "medium" | "low",
    "person_count": 0,
    "description": "Brief description of what you see",
    "objects_detected": ["list of objects"],
    "recommended_action": "What the user should do"
}

If no threats, still describe the scene briefly. Be concise but thorough."""

        client = _get_vision_client()
        image_bytes = base64.b64decode(frame_base64)
        result_text = _generate_content_with_image(client, image_bytes, prompt)

        # Try to parse as JSON, fallback to raw text
        try:
            import json

            # Remove markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            if result.get("threat_detected"):
                severity = result.get("severity", "medium").upper()
                threat_type = result.get("threat_type", "unknown")
                desc = result.get("description", "Threat detected")

                return f"⚠️ THREAT DETECTED [{severity}]\nType: {threat_type}\nDescription: {desc}\nAction: {result.get('recommended_action', 'Stay alert')}"
            else:
                return f"✅ No threats detected. {result.get('description', 'Scene is safe.')}"

        except json.JSONDecodeError:
            return f"Analysis result: {result_text}"

    except Exception as e:
        logger.error(f"❌ Threat analysis error: {e}")
        return f"❌ Error analyzing frame: {str(e)}"


@tool
async def describe_scene(frame_base64: str = None, frame=None) -> str:
    """
    Get a natural language description of what's happening in the camera frame.

    Use this when:
    - User asks "What do you see?"
    - Understanding context of a detection
    - Getting human-readable scene summary

    Args:
        frame_base64: Base64 encoded image (optional)
        frame: OpenCV frame directly (optional)

    Returns:
        Natural language description of the scene.
    """
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not configured. Set GEMINI_API_KEY in .env"

    try:
        if frame is not None and frame_base64 is None:
            frame_base64 = _encode_frame_to_base64(frame)

        if not frame_base64:
            return "❌ No frame provided for analysis"

        client = _get_vision_client()

        prompt = """Describe this security camera image in 2-3 sentences.

Include:
- How many people (if any) and what they appear to be doing
- Notable objects or vehicles
- Overall scene context (indoor/outdoor, time of day if apparent)
- Any unusual activity

Be factual and concise. If no one is present, describe the empty scene."""

        image_bytes = base64.b64decode(frame_base64)
        return _generate_content_with_image(client, image_bytes, prompt)

    except Exception as e:
        logger.error(f"❌ Scene description error: {e}")
        return f"❌ Error describing scene: {str(e)}"


@tool
async def analyze_outfit(frame_base64: str = None, frame=None) -> str:
    """
    Analyze a person's outfit for fashion advice.

    Use this when:
    - User asks "How does my outfit look?"
    - User wants fashion suggestions
    - User asks about clothing coordination

    Args:
        frame_base64: Base64 encoded image (optional)
        frame: OpenCV frame directly (optional)

    Returns:
        Fashion analysis with suggestions.
    """
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not configured. Set GEMINI_API_KEY in .env"

    try:
        if frame is not None and frame_base64 is None:
            frame_base64 = _encode_frame_to_base64(frame)

        if not frame_base64:
            return "❌ No frame provided for analysis"

        client = _get_vision_client()

        prompt = """Analyze this person's outfit and provide fashion advice.

Consider:
1. Color coordination - do the colors work well together?
2. Style consistency - is there a coherent style theme?
3. Fit and proportions (if visible)
4. Suggestions for improvement

Be friendly and constructive. If the outfit looks good, say so!

Respond in this format:
**Current Outfit:** [Describe what they're wearing]
**Color Coordination:** [Rate and explain]
**Style Assessment:** [Your thoughts]
**Suggestions:** [1-2 specific improvements if any]
**Overall Rating:** [1-10 with brief reason]"""

        image_bytes = base64.b64decode(frame_base64)
        return _generate_content_with_image(client, image_bytes, prompt)

    except Exception as e:
        logger.error(f"❌ Outfit analysis error: {e}")
        return f"❌ Error analyzing outfit: {str(e)}"


@tool
async def count_people_in_frame(frame_base64: str = None, frame=None) -> str:
    """
    Count and describe the positions of people in the frame.

    Use this when:
    - User asks "How many people are there?"
    - Understanding crowd size
    - Tracking occupancy

    Args:
        frame_base64: Base64 encoded image (optional)
        frame: OpenCV frame directly (optional)

    Returns:
        Count of people with their approximate positions.
    """
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not configured. Set GEMINI_API_KEY in .env"

    try:
        if frame is not None and frame_base64 is None:
            frame_base64 = _encode_frame_to_base64(frame)

        if not frame_base64:
            return "❌ No frame provided for analysis"

        client = _get_vision_client()

        prompt = """Count the people in this image and describe their positions.

Respond in this exact JSON format:
{
    "count": <number>,
    "positions": [
        {"location": "left/center/right", "activity": "standing/sitting/walking/unknown"},
        ...
    ],
    "confidence": "high/medium/low"
}

If no people, set count to 0. Be accurate - only count actual people."""

        image_bytes = base64.b64decode(frame_base64)
        result_text = _generate_content_with_image(client, image_bytes, prompt)

        try:
            import json

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)
            count = result.get("count", 0)
            confidence = result.get("confidence", "medium")

            if count == 0:
                return "No people detected in the frame."

            positions = result.get("positions", [])
            pos_desc = ", ".join(
                [
                    f"{p.get('location', 'unknown')} ({p.get('activity', 'unknown activity')})"
                    for p in positions
                ]
            )

            return f"👥 {count} person(s) detected (confidence: {confidence})\nPositions: {pos_desc}"

        except json.JSONDecodeError:
            return f"Count result: {result_text}"

    except Exception as e:
        logger.error(f"❌ People counting error: {e}")
        return f"❌ Error counting people: {str(e)}"


@tool
async def understand_scene(frame_base64: str = None, frame=None) -> str:
    """
    Comprehensive scene understanding - analyzes everything happening in the frame.

    Use this when:
    - User asks "What's happening?" or "What's going on?"
    - User wants a complete understanding of the camera view
    - User asks for a security check or situation report
    - Understanding the full context of what the camera sees

    Args:
        frame_base64: Base64 encoded image (optional)
        frame: OpenCV frame directly (optional)

    Returns:
        Comprehensive analysis including people, activities, objects, and safety assessment.
    """
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not configured. Set GEMINI_API_KEY in .env"

    try:
        if frame is not None and frame_base64 is None:
            frame_base64 = _encode_frame_to_base64(frame)

        if not frame_base64:
            return "❌ No frame provided for analysis"

        client = _get_vision_client()

        prompt = """Analyze this camera image and provide a comprehensive understanding of what's happening.

Provide your analysis in this JSON format:
{
    "scene_type": "indoor" | "outdoor" | "unknown",
    "location_description": "Brief description of the location (e.g., 'living room', 'front yard', 'parking lot')",
    "people": {
        "count": <number>,
        "details": [
            {"location": "left/center/right", "activity": "what they're doing", "appearance": "brief description"}
        ]
    },
    "objects_detected": ["list of notable objects"],
    "activities": ["list of activities happening"],
    "time_context": "day/night/twilight/unknown",
    "concerns": ["any concerning observations or empty array"],
    "safety_level": "safe" | "caution" | "alert",
    "summary": "One sentence summary of what's happening"
}

Be thorough but concise. If no people are present, describe the empty scene. Focus on security-relevant details."""

        image_bytes = base64.b64decode(frame_base64)
        result_text = _generate_content_with_image(client, image_bytes, prompt)

        try:
            import json

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            # Build human-readable output
            output_parts = []

            # Scene info
            scene_type = result.get("scene_type", "unknown")
            location = result.get("location_description", "unknown location")
            output_parts.append(f"📍 {scene_type.capitalize()} - {location}")

            # People info
            people = result.get("people", {})
            count = people.get("count", 0)
            if count > 0:
                details = people.get("details", [])
                people_desc = []
                for p in details:
                    people_desc.append(
                        f"  • {p.get('location', '?')}: {p.get('activity', 'unknown activity')}"
                    )
                output_parts.append(
                    f"\n👥 {count} person(s) detected:\n" + "\n".join(people_desc)
                )
            else:
                output_parts.append("\n👤 No people detected in the scene")

            # Objects
            objects = result.get("objects_detected", [])
            if objects:
                output_parts.append(f"\n📦 Objects: {', '.join(objects[:5])}")

            # Activities
            activities = result.get("activities", [])
            if activities:
                output_parts.append(f"\n🎯 Activities: {', '.join(activities)}")

            # Safety
            safety = result.get("safety_level", "safe")
            safety_icon = (
                "✅" if safety == "safe" else "⚠️" if safety == "caution" else "🚨"
            )
            output_parts.append(f"\n{safety_icon} Safety: {safety.upper()}")

            # Concerns
            concerns = result.get("concerns", [])
            if concerns:
                output_parts.append(f"\n⚠️ Concerns: {'; '.join(concerns)}")

            # Summary
            summary = result.get("summary", "")
            if summary:
                output_parts.append(f"\n📝 {summary}")

            return "\n".join(output_parts)

        except json.JSONDecodeError:
            return f"Scene analysis: {result_text}"

    except Exception as e:
        logger.error(f"❌ Scene understanding error: {e}")
        return f"❌ Error understanding scene: {str(e)}"


@tool
async def detect_activity(frame_base64: str = None, frame=None) -> str:
    """
    Detect and classify human activities in the camera frame.

    Use this when:
    - User asks "What are they doing?"
    - Detecting suspicious behavior
    - Understanding human actions

    Args:
        frame_base64: Base64 encoded image (optional)
        frame: OpenCV frame directly (optional)

    Returns:
        Activity classification with confidence level.
    """
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not configured. Set GEMINI_API_KEY in .env"

    try:
        if frame is not None and frame_base64 is None:
            frame_base64 = _encode_frame_to_base64(frame)

        if not frame_base64:
            return "❌ No frame provided for analysis"

        client = _get_vision_client()

        prompt = """Analyze human activities in this image.

Classify activities into categories:
- NORMAL: everyday activities (walking, sitting, talking, working)
- LOITERING: lingering without clear purpose
- SUSPICIOUS: potentially concerning behavior (looking around nervously, trying handles, peering in windows)
- AGGRESSIVE: confrontational or threatening behavior
- DANGER: immediate threat (fighting, weapon visible, breaking in)

Respond in JSON:
{
    "activity_detected": true/false,
    "activities": [
        {"person": "description", "activity": "what they're doing", "classification": "NORMAL/LOITERING/SUSPICIOUS/AGGRESSIVE/DANGER"}
    ],
    "overall_assessment": "NORMAL" | "SUSPICIOUS" | "ALERT",
    "description": "Brief summary of activities"
}

If no people, set activity_detected to false."""

        image_bytes = base64.b64decode(frame_base64)
        result_text = _generate_content_with_image(client, image_bytes, prompt)

        try:
            import json

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            if not result.get("activity_detected"):
                return "No human activity detected in the frame."

            activities = result.get("activities", [])
            assessment = result.get("overall_assessment", "NORMAL")
            description = result.get("description", "")

            icon = (
                "✅"
                if assessment == "NORMAL"
                else "⚠️"
                if assessment == "SUSPICIOUS"
                else "🚨"
            )

            output = [f"{icon} Activity Assessment: {assessment}\n"]

            for a in activities:
                classification = a.get("classification", "NORMAL")
                activity_icon = (
                    "•"
                    if classification == "NORMAL"
                    else "⚠"
                    if classification == "SUSPICIOUS"
                    else "🚨"
                )
                output.append(
                    f"{activity_icon} {a.get('person', 'Person')}: {a.get('activity', 'unknown activity')} [{classification}]"
                )

            output.append(f"\n📝 {description}")

            return "\n".join(output)

        except json.JSONDecodeError:
            return f"Activity result: {result_text}"

    except Exception as e:
        logger.error(f"❌ Activity detection error: {e}")
        return f"❌ Error detecting activity: {str(e)}"


@tool
async def detect_emotions(frame_base64: str = None, frame=None) -> str:
    """
    Detect emotions, facial expressions, and emotional states of people in the frame.

    Use this when:
    - User asks "How do I look?" or "What's my expression?"
    - User wants to know their emotional state
    - Detecting if someone looks sad, happy, crying, stressed, etc.
    - Understanding how someone is feeling

    Args:
        frame_base64: Base64 encoded image (optional)
        frame: OpenCV frame directly (optional)

    Returns:
        Emotional analysis including mood, expressions, and emotional indicators.
    """
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not configured. Set GEMINI_API_KEY in .env"

    try:
        if frame is not None and frame_base64 is None:
            frame_base64 = _encode_frame_to_base64(frame)

        if not frame_base64:
            return "❌ No frame provided for analysis"

        client = _get_vision_client()

        prompt = """Analyze the emotional state of any people visible in this image.

Look for and report on:
1. PRIMARY EMOTION: happy, sad, angry, fearful, surprised, disgusted, neutral, stressed, anxious, excited
2. FACIAL EXPRESSIONS: smiling, frowning, crying, tearful, puffy eyes, red eyes, tense, relaxed
3. EMOTIONAL INDICATORS:
   - Signs of crying: red/puffy eyes, tear tracks, smeared makeup
   - Signs of stress: furrowed brow, tight jaw, tense shoulders
   - Signs of fatigue: dark circles, droopy eyes
   - Signs of happiness: genuine smile (Duchenne smile), relaxed posture
4. BODY LANGUAGE: posture, gestures, tension level
5. OVERALL MOOD: what emotional vibe does the person/project

Respond in JSON format:
{
    "person_detected": true/false,
    "primary_emotion": "emotion name",
    "confidence": "high/medium/low",
    "facial_expressions": ["list of observed expressions"],
    "emotional_indicators": {
        "signs_of_crying": true/false,
        "signs_of_stress": true/false,
        "signs_of_fatigue": true/false,
        "signs_of_happiness": true/false,
        "other_indicators": ["list any other emotional signs"]
    },
    "body_language": "description of posture and body language",
    "overall_mood": "one word mood description",
    "detailed_analysis": "2-3 sentence detailed emotional assessment",
    "possible_reasons": ["list possible reasons for the emotional state"],
    "supportive_message": "a brief supportive message if person seems upset"
}

Be empathetic and accurate. If no person is visible, set person_detected to false."""

        image_bytes = base64.b64decode(frame_base64)
        result_text = _generate_content_with_image(client, image_bytes, prompt)

        try:
            import json

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            if not result.get("person_detected"):
                return "👤 No person detected in the frame to analyze emotions."

            primary = result.get("primary_emotion", "unknown")
            confidence = result.get("confidence", "medium")
            expressions = result.get("facial_expressions", [])
            indicators = result.get("emotional_indicators", {})
            body_lang = result.get("body_language", "")
            mood = result.get("overall_mood", "")
            detailed = result.get("detailed_analysis", "")
            supportive = result.get("supportive_message", "")

            # Build emoji based on emotion
            emotion_emoji = {
                "happy": "😊",
                "sad": "😢",
                "angry": "😠",
                "fearful": "😨",
                "surprised": "😲",
                "disgusted": "😒",
                "neutral": "😐",
                "stressed": "😰",
                "anxious": "😟",
                "excited": "🤩",
            }.get(primary.lower(), "🙂")

            output_parts = [
                f"{emotion_emoji} **Emotional State: {primary.upper()}** (confidence: {confidence})",
                "",
            ]

            if expressions:
                output_parts.append(f"Facial Expressions: {', '.join(expressions)}")

            # Emotional indicators
            ind_parts = []
            if indicators.get("signs_of_crying"):
                ind_parts.append("💧 Signs of crying detected")
            if indicators.get("signs_of_stress"):
                ind_parts.append("😓 Signs of stress detected")
            if indicators.get("signs_of_fatigue"):
                ind_parts.append("😴 Signs of fatigue detected")
            if indicators.get("signs_of_happiness"):
                ind_parts.append("✨ Signs of happiness detected")

            other = indicators.get("other_indicators", [])
            for o in other:
                ind_parts.append(f"• {o}")

            if ind_parts:
                output_parts.append("\nEmotional Indicators:\n" + "\n".join(ind_parts))

            if body_lang:
                output_parts.append(f"\n🧍 Body Language: {body_lang}")

            if mood:
                output_parts.append(f"\n🎭 Overall Mood: {mood}")

            if detailed:
                output_parts.append(f"\n📝 {detailed}")

            if supportive and primary.lower() in [
                "sad",
                "stressed",
                "anxious",
                "fearful",
                "angry",
            ]:
                output_parts.append(f"\n💚 {supportive}")

            return "\n".join(output_parts)

        except json.JSONDecodeError:
            return f"Emotion analysis: {result_text}"

    except Exception as e:
        logger.error(f"❌ Emotion detection error: {e}")
        return f"❌ Error detecting emotions: {str(e)}"


@tool
async def analyze_person(frame_base64: str = None, frame=None) -> str:
    """
    Comprehensive analysis of a person in the frame - appearance, emotions, and context.

    Use this when:
    - User asks "How do I look?" (general appearance + emotion)
    - User wants complete personal analysis
    - Getting full context about a person on camera

    Args:
        frame_base64: Base64 encoded image (optional)
        frame: OpenCV frame directly (optional)

    Returns:
        Complete analysis including appearance, emotions, and recommendations.
    """
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not configured. Set GEMINI_API_KEY in .env"

    try:
        if frame is not None and frame_base64 is None:
            frame_base64 = _encode_frame_to_base64(frame)

        if not frame_base64:
            return "❌ No frame provided for analysis"

        client = _get_vision_client()

        prompt = """Provide a comprehensive analysis of the person in this image.

Analyze:
1. APPEARANCE:
   - Clothing: style, colors, coordination
   - Grooming: hair, overall look
   - General presentation

2. EMOTIONAL STATE:
   - Current mood and expressions
   - Signs of stress, tiredness, or strong emotions
   - Body language

3. CONTEXT:
   - What they appear to be doing
   - Setting/location context
   - Time context (if apparent)

4. OVERALL IMPRESSION:
   - How they present themselves
   - Any notable observations

Respond in JSON:
{
    "appearance": {
        "clothing": "description",
        "style": "casual/formal/etc",
        "colors": ["list of main colors"],
        "coordination": "well coordinated/could improve/etc",
        "grooming": "description of hair and overall grooming"
    },
    "emotional_state": {
        "mood": "primary mood",
        "expressions": ["list"],
        "energy_level": "high/medium/low",
        "emotional_notes": "any notable emotional observations"
    },
    "context": {
        "activity": "what they're doing",
        "location": "indoor/outdoor and type",
        "time_of_day": "morning/afternoon/evening/night/unknown"
    },
    "overall_impression": "2-3 sentence summary",
    "suggestions": ["any helpful suggestions"],
    "compliments": ["genuine compliments about appearance or vibe"]
}

Be observant, honest, and kind. If no person is visible, say so."""

        image_bytes = base64.b64decode(frame_base64)
        result_text = _generate_content_with_image(client, image_bytes, prompt)

        try:
            import json

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            output_parts = ["👤 **Personal Analysis**\n"]

            # Appearance
            appearance = result.get("appearance", {})
            if appearance:
                output_parts.append("👔 **Appearance:**")
                output_parts.append(f"   Clothing: {appearance.get('clothing', 'N/A')}")
                output_parts.append(f"   Style: {appearance.get('style', 'N/A')}")
                output_parts.append(
                    f"   Colors: {', '.join(appearance.get('colors', []))}"
                )
                output_parts.append(
                    f"   Coordination: {appearance.get('coordination', 'N/A')}"
                )
                output_parts.append(f"   Grooming: {appearance.get('grooming', 'N/A')}")

            # Emotional State
            emotional = result.get("emotional_state", {})
            if emotional:
                output_parts.append(f"\n😊 **Emotional State:**")
                output_parts.append(f"   Mood: {emotional.get('mood', 'N/A')}")
                output_parts.append(
                    f"   Energy: {emotional.get('energy_level', 'N/A')}"
                )
                if emotional.get("expressions"):
                    output_parts.append(
                        f"   Expressions: {', '.join(emotional.get('expressions', []))}"
                    )
                if emotional.get("emotional_notes"):
                    output_parts.append(f"   Notes: {emotional.get('emotional_notes')}")

            # Context
            context = result.get("context", {})
            if context:
                output_parts.append(f"\n📍 **Context:**")
                output_parts.append(f"   Activity: {context.get('activity', 'N/A')}")
                output_parts.append(f"   Location: {context.get('location', 'N/A')}")

            # Overall
            overall = result.get("overall_impression", "")
            if overall:
                output_parts.append(f"\n✨ **Overall:** {overall}")

            # Suggestions
            suggestions = result.get("suggestions", [])
            if suggestions:
                output_parts.append(f"\n💡 **Suggestions:**")
                for s in suggestions:
                    output_parts.append(f"   • {s}")

            # Compliments
            compliments = result.get("compliments", [])
            if compliments:
                output_parts.append(f"\n💜 **Compliments:**")
                for c in compliments:
                    output_parts.append(f"   • {c}")

            return "\n".join(output_parts)

        except json.JSONDecodeError:
            return f"Analysis result: {result_text}"

    except Exception as e:
        logger.error(f"❌ Person analysis error: {e}")
        return f"❌ Error analyzing person: {str(e)}"


vision_tools = [
    analyze_frame_for_threats,
    describe_scene,
    analyze_outfit,
    count_people_in_frame,
    understand_scene,
    detect_activity,
    detect_emotions,
    analyze_person,
]
