"""
Vision Tools using NVIDIA NIM API via LangChain for cloud-based vision analysis.
No local GPU required - uses cloud inference with LangChain compatibility.

Enhanced with Helper Agent for:
- Verification of vision output
- Deduplication of text
- Improved emotion detection
- User-friendly formatting
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

HELPER_ENABLED = os.getenv("HELPER_AGENT_ENABLED", "true").lower() == "true"

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

        prompt = """Quick security threat analysis. Be BRIEF.

**Threat Level:** [NONE/LOW/MEDIUM/HIGH]
**People:** [count]
**Weapons:** [yes/no - type if yes]
**Suspicious:** [yes/no - what]
**Action:** [recommended action if threat]

Rules: Max 40 words, no repetition"""

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

        prompt = """Describe this image in 2 sentences max. Include: people count, activity, setting. Be factual, no repetition."""

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

        prompt = """Analyze outfit briefly. Format:
**Outfit:** [clothing items and colors]
**Style:** [casual/formal/etc]
**Rating:** [1-10 with brief reason]

Max 30 words, no repetition."""

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

        prompt = """Count people. Format: "X people: [position and activity for each]". If none, say "No people". Max 20 words."""

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

        prompt = """Analyze this camera image. Provide a BRIEF response in this exact format:

**Scene:** [Indoor/Outdoor - location]
**People:** [count and brief activity]
**Objects:** [notable items only]
**Safety:** [Safe/Concerning - reason]
**Summary:** [one sentence]

Rules:
- Be concise, no repetition
- Max 50 words total
- No detailed descriptions unless asked"""

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

        prompt = """Classify activity: NORMAL/SUSPICIOUS/AGGRESSIVE. Describe briefly in one sentence. Max 20 words."""

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

        prompt = """Detect YOUR emotional state (you are the user in this image). Format:
**Mood:** [your primary emotion]
**Signs:** [your facial/body indicators]
**Energy:** [high/medium/low]

IMPORTANT: Address the user directly as "you" - NOT "this person" or "the person".

Max 25 words, be empathetic and use "you/your"."""

        raw_result = await _analyze_image(image_base64, prompt)

        logger.info(f"[VISION] NVIDIA raw result: {raw_result[:200]}...")

        if HELPER_ENABLED:
            try:
                from app.agents.helper_agent import get_helper_agent, QueryType

                helper = get_helper_agent()
                verified = await helper.verify_and_format(
                    raw_output=raw_result,
                    image_base64=image_base64,
                    query_type=QueryType.EMOTION,
                )

                logger.info(f"[VISION] Helper Agent success: {verified.get('success')}")
                logger.info(
                    f"[VISION] Helper Agent response: {verified.get('formatted_response', 'N/A')[:200]}..."
                )

                if verified.get("success"):
                    return verified.get("formatted_response", raw_result)
                else:
                    return raw_result
            except Exception as helper_error:
                logger.warning(
                    f"Helper Agent failed for emotions, using raw result: {helper_error}"
                )
                return raw_result

        return raw_result

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

        prompt = """Analyze the person in this image (this is the user asking). Be BRIEF and direct.

**Appearance:** [your clothing, colors, style in one line]
**Mood:** [your emotional state, energy level]
**Activity:** [what you are doing]
**Verdict:** [one sentence compliment]

IMPORTANT: Always address the user directly as "you" - NOT "this person" or "the person".

Rules:
- Max 60 words total
- No repetition
- Use "you" and "your" - the person in the image IS the user
- End with a genuine compliment
- If no person visible, say "No person detected in frame"
"""

        raw_result = await _analyze_image(image_base64, prompt)

        logger.info(f"[VISION] analyze_person NVIDIA raw result: {raw_result[:200]}...")

        if HELPER_ENABLED:
            try:
                from app.agents.helper_agent import get_helper_agent, QueryType

                helper = get_helper_agent()
                verified = await helper.verify_and_format(
                    raw_output=raw_result,
                    image_base64=image_base64,
                    query_type=QueryType.APPEARANCE,
                )

                logger.info(
                    f"[VISION] analyze_person Helper Agent success: {verified.get('success')}"
                )
                logger.info(
                    f"[VISION] analyze_person Helper Agent response: {verified.get('formatted_response', 'N/A')[:200]}..."
                )

                if verified.get("success"):
                    return verified.get("formatted_response", raw_result)
                else:
                    return raw_result
            except Exception as helper_error:
                logger.warning(f"Helper Agent failed, using raw result: {helper_error}")
                return raw_result

        return raw_result

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
