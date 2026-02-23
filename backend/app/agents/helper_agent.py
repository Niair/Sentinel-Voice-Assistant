"""
Helper Agent using Ollama Qwen 3.5 for:
- Verification of Security Agent output
- Formatting and deduplication
- Emotion analysis improvement
- Threat categorization
- User-friendly response generation

This agent runs after the Security Agent (NVIDIA Vision) to:
1. Re-analyze frames for verification
2. Remove duplicate text
3. Improve emotion detection accuracy
4. Format responses for user-friendliness
5. Categorize threats (NORMAL/CAUTION/ALERT)
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from datetime import datetime

from langchain_ollama import OllamaLLM
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

OLLAMA_MODEL = os.getenv("HELPER_AGENT_MODEL", "qwen3-coder:480b-cloud")
OLLAMA_FALLBACK_MODEL = os.getenv("HELPER_AGENT_FALLBACK_MODEL", "glm-5:cloud")


class ThreatCategory(str, Enum):
    NORMAL = "normal"
    CAUTION = "caution"
    ALERT = "alert"


class QueryType(str, Enum):
    APPEARANCE = "appearance"
    EMOTION = "emotion"
    SCENE = "scene"
    SECURITY = "security"
    OBJECT_SEARCH = "object_search"


HELPER_SYSTEM_PROMPT = """You are a helpful AI assistant that cleans up and formats vision analysis results.

Your tasks:
1. Remove any duplicate or repetitive text
2. Fix formatting issues (missing spaces, merged words)
3. Make the response user-friendly and empathetic
4. For emotion queries, be supportive and warm

IMPORTANT: You CANNOT see the image. Only clean up the text provided.
Do NOT claim to analyze or verify the image visually.

Rules:
- Be concise (max 100 words for responses)
- No repetition
- Be empathetic and supportive
- Use emojis sparingly and appropriately
- Fix formatting issues like "LowYou" -> "Low. You"
"""


class HelperAgent:
    """
    Helper Agent using Ollama Qwen 3.5 for verification and formatting.

    Features:
    - Vision capability for re-analysis (via cloud model)
    - Deduplication of text
    - Emotion detection improvement
    - Threat categorization
    - User-friendly formatting
    """

    def __init__(self):
        self.llm = OllamaLLM(model=OLLAMA_MODEL)
        self.model_name = OLLAMA_MODEL
        self._fallback_llm = None
        self._use_fallback = False
        logger.info(f"✅ Helper Agent initialized with {OLLAMA_MODEL}")

    def _get_llm(self):
        """Get LLM instance, with fallback support."""
        if self._use_fallback and self._fallback_llm:
            return self._fallback_llm
        return self.llm

    async def _invoke_with_fallback(self, prompt: str) -> str:
        """Invoke LLM with fallback support."""
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            if "not found" in str(e) or "404" in str(e):
                logger.warning(
                    f"⚠️ Primary model failed, trying fallback: {OLLAMA_FALLBACK_MODEL}"
                )
                if self._fallback_llm is None:
                    self._fallback_llm = OllamaLLM(model=OLLAMA_FALLBACK_MODEL)
                self._use_fallback = True
                return self._fallback_llm.invoke(prompt)
            raise

    async def verify_and_format(
        self,
        raw_output: str,
        image_base64: str,
        query_type: QueryType = QueryType.SCENE,
    ) -> Dict[str, Any]:
        """
        Main method: Verify Security Agent output and format response.

        Args:
            raw_output: Raw output from Security Agent (NVIDIA)
            image_base64: Original frame for context (passed for potential future use)
            query_type: Type of query (appearance, emotion, scene, security)

        Returns:
            Dict with verified, formatted response
        """
        try:
            prompt = self._build_verification_prompt(raw_output, query_type)

            response = await self._invoke_with_fallback(prompt)

            cleaned_response = self._clean_duplicates(response)
            formatted_response = self._format_response(cleaned_response, query_type)

            return {
                "success": True,
                "raw_output": raw_output,
                "verified_output": response,
                "formatted_response": formatted_response,
                "query_type": query_type.value,
                "model_used": self.model_name
                if not self._use_fallback
                else OLLAMA_FALLBACK_MODEL,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Helper Agent verification failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_output": raw_output,
                "formatted_response": self._clean_duplicates(raw_output),
            }

    async def verify_security_output(
        self, security_result: Dict[str, Any], image_base64: str
    ) -> Tuple[ThreatCategory, Dict[str, Any]]:
        """
        Verify Security Agent's detection result for background monitoring.

        Args:
            security_result: Raw detection result from Security Agent
            image_base64: Original frame for verification

        Returns:
            Tuple of (ThreatCategory, verified_result)
        """
        try:
            raw_analysis = security_result.get(
                "raw_analysis", security_result.get("description", "")
            )

            verification_prompt = f"""Analyze this security detection and verify its accuracy.

Original Detection:
{raw_analysis}

Your task:
1. Determine if this is a genuine security concern
2. Categorize the threat level
3. Provide a brief, factual summary

Respond in this JSON format:
{{
    "verified": true/false,
    "category": "normal" or "caution" or "alert",
    "person_count": <number>,
    "has_weapon": true/false,
    "is_suspicious": true/false,
    "description": "Brief factual description",
    "action_recommended": "What action if any is needed"
}}

Categories:
- normal: Routine detection (person walking by, pet, etc.)
- caution: Something unusual but not dangerous
- alert: Genuine threat (weapon, break-in, violence)
"""

            response = await self._invoke_with_fallback(verification_prompt)

            parsed = self._parse_json_response(response)

            category = self._map_category(parsed.get("category", "normal"))

            verified_result = {
                **security_result,
                "verified": parsed.get("verified", True),
                "category": category.value,
                "person_count": parsed.get("person_count", 0),
                "has_weapon": parsed.get("has_weapon", False),
                "is_suspicious": parsed.get("is_suspicious", False),
                "description": parsed.get("description", raw_analysis),
                "action_recommended": parsed.get("action_recommended", ""),
                "model_used": self.model_name
                if not self._use_fallback
                else OLLAMA_FALLBACK_MODEL,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return category, verified_result

        except Exception as e:
            logger.error(f"❌ Security verification failed: {e}")
            return ThreatCategory.NORMAL, {
                **security_result,
                "error": str(e),
                "category": "normal",
            }

    async def analyze_emotions(
        self, image_base64: str, context: str = ""
    ) -> Dict[str, Any]:
        """
        Dedicated emotion analysis using Qwen 3.5.

        Args:
            image_base64: Base64 encoded image
            context: Additional context from previous analysis

        Returns:
            Dict with emotion analysis
        """
        try:
            emotion_prompt = f"""Analyze the emotional state of the person in this image.

Previous context (if any): {context}

Provide a thoughtful, empathetic analysis in this format:

**Primary Emotion:** [happy/sad/neutral/stressed/angry/contemplative/excited]
**Confidence:** [high/medium/low]
**Indicators:** [What facial/body cues suggest this emotion]
**Energy Level:** [high/medium/low]
**Summary:** [One supportive sentence about their emotional state]

Rules:
- Be empathetic and supportive
- If uncertain, acknowledge it
- If the person seems distressed, offer kind words
- Keep response under 80 words
"""

            response = await self._invoke_with_fallback(emotion_prompt)

            cleaned = self._clean_duplicates(response)

            primary_emotion = self._extract_emotion(cleaned)

            return {
                "success": True,
                "emotion_analysis": cleaned,
                "primary_emotion": primary_emotion,
                "model_used": self.model_name
                if not self._use_fallback
                else OLLAMA_FALLBACK_MODEL,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Emotion analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "emotion_analysis": "Unable to analyze emotions at this time.",
            }

    def categorize_threat(self, result: Dict[str, Any]) -> ThreatCategory:
        """
        Categorize detection result into NORMAL/CAUTION/ALERT.

        Args:
            result: Detection result dictionary

        Returns:
            ThreatCategory enum value
        """
        if result.get("has_weapon", False):
            return ThreatCategory.ALERT

        if result.get("is_suspicious", False):
            return ThreatCategory.CAUTION

        if result.get("category"):
            return self._map_category(result["category"])

        threat_level = result.get("threat_level", "").lower()
        if threat_level in ["high", "critical"]:
            return ThreatCategory.ALERT
        elif threat_level == "medium":
            return ThreatCategory.CAUTION

        severity = result.get("severity", "").lower()
        if severity == "high":
            return ThreatCategory.ALERT
        elif severity == "medium":
            return ThreatCategory.CAUTION

        return ThreatCategory.NORMAL

    def should_send_email(self, category: ThreatCategory, details: Dict) -> bool:
        """
        Determine if email should be sent for this threat level.

        Email is sent for:
        - ALERT: Always
        - CAUTION: Only if confirmed suspicious activity

        Args:
            category: ThreatCategory
            details: Additional details about the detection

        Returns:
            True if email should be sent
        """
        if category == ThreatCategory.ALERT:
            return True

        if category == ThreatCategory.CAUTION:
            return details.get("is_suspicious", False) and details.get("verified", True)

        return False

    def _build_verification_prompt(self, raw_output: str, query_type: QueryType) -> str:
        """Build prompt for cleanup based on query type."""

        base_prompt = f"""{HELPER_SYSTEM_PROMPT}

Original Analysis (may have duplicates or formatting issues):
{raw_output}

"""

        if query_type == QueryType.APPEARANCE:
            base_prompt += """The user asked about their appearance. Please:
1. Remove any duplicate sentences or paragraphs
2. Fix formatting issues (e.g., "LowYou" -> "Low. You")
3. Make the response friendly and complimentary
4. Keep it concise and warm
5. End with a genuine, positive comment

Format your response in a friendly, conversational style. Do NOT claim to see or analyze the image."""

        elif query_type == QueryType.EMOTION:
            base_prompt += """The user asked about their emotional state. Please:
1. Clean up the emotional description
2. Be empathetic and supportive
3. Remove any repeated or contradictory statements
4. Keep the tone warm and caring
5. Fix any formatting issues

Format your response warmly. Do NOT claim to see or verify the image."""

        elif query_type == QueryType.SECURITY:
            base_prompt += """The user asked about security/threats. Please:
1. Clean up the response
2. Be factual and clear
3. Remove any repeated text
4. Keep it concise

Format your response to be informative but not alarming."""

        else:
            base_prompt += """The user asked about the scene/situation. Please:
1. Clean up the response
2. Remove any repeated text
3. Make it clear and informative
4. Fix any formatting issues

Format your response clearly."""

        return base_prompt

    def _clean_duplicates(self, text: str) -> str:
        """
        Remove duplicate sentences/paragraphs from text.

        Handles the issue where NVIDIA vision model echoes content.
        """
        if not text:
            return text

        lines = text.split("\n")
        seen = set()
        unique_lines = []

        for line in lines:
            normalized = " ".join(line.lower().split())

            if normalized and normalized not in seen:
                if len(normalized) > 20:
                    is_duplicate = False
                    for seen_line in seen:
                        if self._similar_text(normalized, seen_line, threshold=0.8):
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        seen.add(normalized)
                        unique_lines.append(line)
                else:
                    seen.add(normalized)
                    unique_lines.append(line)

        result = "\n".join(unique_lines)

        result = re.sub(r"\n{3,}", "\n\n", result)
        result = re.sub(r" {2,}", " ", result)

        return result.strip()

    def _similar_text(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Check if two texts are similar above threshold."""
        if not text1 or not text2:
            return False

        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return False

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        similarity = intersection / union if union > 0 else 0

        return similarity >= threshold

    def _format_response(self, text: str, query_type: QueryType) -> str:
        """Format response based on query type for user-friendliness."""

        formatted = text.strip()

        if query_type == QueryType.APPEARANCE:
            if not any(emoji in formatted for emoji in ["😊", "👍", "✨", "💜", "💙"]):
                formatted += " 😊"

        elif query_type == QueryType.EMOTION:
            if "stress" in formatted.lower() or "sad" in formatted.lower():
                if "here for you" not in formatted.lower():
                    formatted += " 💙 I'm here if you want to talk."

        return formatted

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from response: {response[:100]}...")
            return {}

    def _map_category(self, category_str: str) -> ThreatCategory:
        """Map string category to ThreatCategory enum."""
        category_map = {
            "normal": ThreatCategory.NORMAL,
            "caution": ThreatCategory.CAUTION,
            "alert": ThreatCategory.ALERT,
            "warning": ThreatCategory.CAUTION,
            "threat": ThreatCategory.ALERT,
            "high": ThreatCategory.ALERT,
            "medium": ThreatCategory.CAUTION,
            "low": ThreatCategory.NORMAL,
        }
        return category_map.get(category_str.lower(), ThreatCategory.NORMAL)

    def _extract_emotion(self, text: str) -> str:
        """Extract primary emotion from emotion analysis text."""
        emotion_keywords = {
            "happy": ["happy", "joy", "cheerful", "pleased", "delighted"],
            "sad": ["sad", "unhappy", "down", "depressed", "melancholy"],
            "neutral": ["neutral", "calm", "relaxed", "composed"],
            "stressed": ["stressed", "anxious", "worried", "tense", "nervous"],
            "angry": ["angry", "frustrated", "irritated", "annoyed"],
            "contemplative": ["contemplative", "thoughtful", "reflective"],
            "excited": ["excited", "enthusiastic", "energetic", "thrilled"],
        }

        text_lower = text.lower()

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return emotion

        return "neutral"


_helper_agent: Optional[HelperAgent] = None


def get_helper_agent() -> HelperAgent:
    """Get or create Helper Agent singleton."""
    global _helper_agent
    if _helper_agent is None:
        _helper_agent = HelperAgent()
    return _helper_agent
