"""
Vision Tools using NVIDIA NIM API via LangChain for cloud-based vision analysis.
No local GPU required - uses cloud inference with LangChain compatibility.
"""

import os
import base64
import logging
from typing import Optional, Dict, Any

from langchain_core.tools import tool
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

NVIDIA_API_KEY = os.getenv("NVEDIAKIMIK2_API_KEY", "")
VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"

_vision_llm = None


def _get_vision_llm():
    """Get NVIDIA Vision LLM instance."""
    global _vision_llm
    if _vision_llm is None:
        if not NVIDIA_API_KEY:
            raise ValueError(
                "NVIDIA API key not found. Set NVEDIAKIMIK2_API_KEY in .env"
            )
        _vision_llm = ChatNVIDIA(
            model=VISION_MODEL,
            nvidia_api_key=NVIDIA_API_KEY,
            temperature=0.2,
            max_tokens=1024,
        )
        logger.info(f"Vision LLM initialized: {VISION_MODEL}")
    return _vision_llm


def _ensure_base64(frame_base64: str = None, frame=None) -> str:
    """Ensure we have base64 encoded image."""
    if frame_base64:
        return frame_base64
    if frame is not None:
        import cv2

        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buffer).decode("utf-8")
    return None


async def _analyze_image(image_base64: str, prompt: str) -> str:
    """Analyze image using NVIDIA Vision LLM."""
    try:
        llm = _get_vision_llm()

        image_url = f"data:image/jpeg;base64,{image_base64}"

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        )

        response = await llm.ainvoke([message])
        return response.content

    except Exception as e:
        logger.error(f"Vision analysis error: {e}")
        return f"Vision analysis failed: {str(e)}"


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
    try:
        image_base64 = _ensure_base64(frame_base64, frame)
        if not image_base64:
            return "No frame provided for analysis"

        prompt = """Analyze this security camera image for potential threats.

Look for:
1. WEAPONS: knives, guns, baseball bats, sharp objects, blunt weapons
2. THREATENING BEHAVIOR: aggressive postures, raised fists, chasing
3. SUSPICIOUS OBJECTS: masks, gloves (worn by non-workers), crowbars
4. PEOPLE: count and note their positions

Provide a brief threat assessment:
- Threat level: NONE/LOW/MEDIUM/HIGH
- What you see
- Recommended action if any threat detected"""

        result = await _analyze_image(image_base64, prompt)
        return result

    except Exception as e:
        logger.error(f"Threat analysis error: {e}")
        return f"Error analyzing frame: {str(e)}"


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
    try:
        image_base64 = _ensure_base64(frame_base64, frame)
        if not image_base64:
            return "No frame provided for analysis"

        prompt = """Describe this camera image in 2-3 sentences.

Include:
- How many people (if any) and what they appear to be doing
- Notable objects or vehicles
- Overall scene context (indoor/outdoor)

Be factual and concise."""

        result = await _analyze_image(image_base64, prompt)
        return result

    except Exception as e:
        logger.error(f"Scene description error: {e}")
        return f"Error describing scene: {str(e)}"


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
    try:
        image_base64 = _ensure_base64(frame_base64, frame)
        if not image_base64:
            return "No frame provided for analysis"

        prompt = """Analyze this person's outfit and provide fashion advice.

Consider:
1. Color coordination
2. Style consistency
3. Overall presentation

Be friendly and constructive!

Format:
**Current Outfit:** [Describe what they're wearing]
**Style Assessment:** [Your thoughts]
**Overall:** [1-2 sentence summary]"""

        result = await _analyze_image(image_base64, prompt)
        return result

    except Exception as e:
        logger.error(f"Outfit analysis error: {e}")
        return f"Error analyzing outfit: {str(e)}"


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
    try:
        image_base64 = _ensure_base64(frame_base64, frame)
        if not image_base64:
            return "No frame provided for analysis"

        prompt = """Count the people in this image.

Respond with:
- Total count
- Where each person is (left/center/right)
- What each person appears to be doing

If no people, say "No people detected"."""

        result = await _analyze_image(image_base64, prompt)
        return result

    except Exception as e:
        logger.error(f"People counting error: {e}")
        return f"Error counting people: {str(e)}"


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
    try:
        image_base64 = _ensure_base64(frame_base64, frame)
        if not image_base64:
            return "No frame provided for analysis"

        prompt = """Analyze this camera image comprehensively.

Provide:
1. **Scene Type:** Indoor/Outdoor and location type
2. **People:** Count and what they're doing
3. **Objects:** Notable objects visible
4. **Activities:** What's happening
5. **Safety:** Is this scene safe or concerning?
6. **Summary:** One sentence summary

Be thorough but concise."""

        result = await _analyze_image(image_base64, prompt)
        return result

    except Exception as e:
        logger.error(f"Scene understanding error: {e}")
        return f"Error understanding scene: {str(e)}"


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
    try:
        image_base64 = _ensure_base64(frame_base64, frame)
        if not image_base64:
            return "No frame provided for analysis"

        prompt = """What are the people in this image doing?

Classify as:
- NORMAL: everyday activities (walking, sitting, talking)
- SUSPICIOUS: concerning behavior (looking around nervously, trying handles)
- AGGRESSIVE: threatening behavior

Provide a brief description."""

        result = await _analyze_image(image_base64, prompt)
        return result

    except Exception as e:
        logger.error(f"Activity detection error: {e}")
        return f"Error detecting activity: {str(e)}"


@tool
async def detect_emotions(frame_base64: str = None, frame=None) -> str:
    """
    Detect emotions, facial expressions, and emotional states of people in the frame.

    Use this when:
    - User asks "How do I look?" or "What's my expression?"
    - User wants to know their emotional state
    - Detecting if someone looks sad, happy, crying, stressed, etc.

    Args:
        frame_base64: Base64 encoded image (optional)
        frame: OpenCV frame directly (optional)

    Returns:
        Emotional analysis including mood, expressions, and emotional indicators.
    """
    try:
        image_base64 = _ensure_base64(frame_base64, frame)
        if not image_base64:
            return "No frame provided for analysis"

        prompt = """Analyze the emotional state of people in this image.

Look for:
1. Primary emotion: happy, sad, stressed, tired, neutral
2. Facial expressions
3. Body language
4. Overall mood

Be empathetic and descriptive."""

        result = await _analyze_image(image_base64, prompt)
        return result

    except Exception as e:
        logger.error(f"Emotion detection error: {e}")
        return f"Error detecting emotions: {str(e)}"


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
    try:
        image_base64 = _ensure_base64(frame_base64, frame)
        if not image_base64:
            return "No frame provided for analysis"

        prompt = """Provide a comprehensive analysis of the person in this image.

Analyze:
1. **Appearance:** Clothing, style, colors, grooming
2. **Emotional State:** Mood, expressions, energy level
3. **Context:** What they're doing, where they are
4. **Overall Impression:** How they present themselves

Be observant, honest, and kind. If no person is visible, say so.

End with a genuine compliment."""

        result = await _analyze_image(image_base64, prompt)
        return result

    except Exception as e:
        logger.error(f"Person analysis error: {e}")
        return f"Error analyzing person: {str(e)}"


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
