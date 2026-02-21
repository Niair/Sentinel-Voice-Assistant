"""
Security Agent using Qwen2-VL-7B for local vision analysis.

This agent runs locally on GPU and analyzes camera frames for:
- Person detection and counting
- Activity recognition
- Object detection (laptops, bags, etc.)
- Threat assessment
- Scene description
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "Qwen/Qwen2-VL-7B-Instruct"
DEVICE = "cuda"  # Use GPU

# Singleton instance
_security_agent = None


class SecurityAgent:
    """
    Security Agent using Qwen2-VL-7B for vision analysis.

    Features:
    - Lazy loading (only loads when needed)
    - Automatic unloading after inactivity
    - GPU memory management
    """

    def __init__(self):
        self.model_name = MODEL_NAME
        self.processor = None
        self.model = None
        self.device = DEVICE
        self.last_used_time = None
        self.auto_unload_seconds = 30  # Unload after 30 seconds of inactivity

    def is_loaded(self) -> bool:
        """Check if model is loaded in GPU memory."""
        return self.model is not None

    def load(self) -> bool:
        """
        Load Qwen2-VL-7B model to GPU.

        Returns:
            True if loaded successfully, False otherwise
        """
        if self.model is not None:
            logger.info("Security Agent already loaded")
            return True

        try:
            logger.info(
                "Loading Qwen2-VL-7B Security Agent (4-bit quantization for 8GB VRAM)..."
            )
            from transformers import (
                Qwen2VLForConditionalGeneration,
                AutoProcessor,
                BitsAndBytesConfig,
            )
            import torch

            self.processor = AutoProcessor.from_pretrained(
                self.model_name, trust_remote_code=True
            )

            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )

            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True,
            )

            logger.info("✅ Qwen2-VL-7B Security Agent loaded successfully")
            self.last_used_time = datetime.utcnow()
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load Qwen2-VL-7B: {e}")
            return False

    def unload(self):
        """
        Unload model from GPU to save memory.
        """
        if self.model is None:
            return

        try:
            del self.model
            del self.processor
            self.model = None
            self.processor = None

            # Clear GPU cache
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("✅ Qwen2-VL-7B Security Agent unloaded")

        except Exception as e:
            logger.error(f"❌ Error unloading model: {e}")

    def check_and_unload(self):
        """Check if should unload based on inactivity."""
        if self.model is None or self.last_used_time is None:
            return

        time_since_use = (datetime.utcnow() - self.last_used_time).total_seconds()
        if time_since_use > self.auto_unload_seconds:
            self.unload()

    def _update_frame_time(self):
        """Update last used timestamp."""
        self.last_used_time = datetime.utcnow()

    def _convert_frame_to_pil(self, frame) -> Optional[Any]:
        """Convert OpenCV frame to PIL Image."""
        try:
            import cv2
            from PIL import Image

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            return pil_image
        except Exception as e:
            logger.error(f"❌ Error converting frame: {e}")
            return None

    def _encode_frame_to_base64(self, frame) -> Optional[str]:
        """Convert OpenCV frame to base64."""
        try:
            import cv2

            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return base64.b64encode(bytes(buffer)).decode("utf-8")
        except Exception as e:
            logger.error(f"❌ Error encoding frame: {e}")
            return None

    async def analyze(
        self, frame, prompt: str = None, frame_base64: str = None
    ) -> Dict[str, Any]:
        """
        Analyze camera frame using Qwen2-VL.

        Args:
            frame: OpenCV frame (numpy array)
            prompt: Custom prompt (optional)
            frame_base64: Base64 encoded frame (alternative to frame)

        Returns:
            Dictionary with analysis results
        """
        # Load model if not loaded
        if not self.is_loaded():
            if not self.load():
                return {
                    "success": False,
                    "error": "Failed to load Security Agent model",
                }

        try:
            # Convert frame to PIL Image
            pil_image = None
            if frame is not None:
                pil_image = self._convert_frame_to_pil(frame)
            elif frame_base64 is not None:
                import base64
                from PIL import Image
                import io

                image_bytes = base64.b64decode(frame_base64)
                pil_image = Image.open(io.BytesIO(image_bytes))

            if pil_image is None:
                return {"success": False, "error": "No valid image provided"}

            # Default security prompt
            if prompt is None:
                prompt = """Analyze this security camera image and provide:
1. How many people do you see?
2. What are they doing?
3. Do you see any weapons or suspicious objects?
4. Is there anything concerning or unusual?
5. Describe the scene briefly.

Respond in JSON format:
{
    "person_count": <number>,
    "activities": ["list of activities"],
    "has_weapon": true/false,
    "suspicious_objects": ["list if any"],
    "is_suspicious": true/false,
    "scene_description": "brief description",
    "threat_level": "low/medium/high"
}"""

            # Prepare messages
            from qwen_vl_utils import process_vision_info

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": pil_image},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            # Process vision info
            text_prompt = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            input_ids = self.processor(
                text=[text_prompt],
                images=process_vision_info(messages),
                return_tensors="pt",
                padding=True,
            )

            # Move to same device as model
            import torch

            model_device = next(self.model.parameters()).device
            input_ids = {k: v.to(model_device) for k, v in input_ids.items()}

            # Generate
            generated_ids = self.model.generate(
                **input_ids,
                max_new_tokens=512,
                do_sample=False,
                temperature=0.1,
            )

            # Decode
            generated_ids = [
                out_ids[len(in_ids) :]
                for in_ids, out_ids in zip(input_ids["input_ids"], generated_ids)
            ]

            response = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )[0].strip()

            # Update last used time
            self._update_frame_time()

            # Parse JSON response
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"❌ Error analyzing frame: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse Qwen2 response to extract structured data."""
        import json

        # Try to extract JSON from response
        try:
            # Find JSON in response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            # Try to parse as JSON
            result = json.loads(response)
            return {"success": True, **result}
        except json.JSONDecodeError:
            # Return raw response if JSON parsing fails
            return {
                "success": True,
                "raw_response": response,
                "person_count": 0,
                "threat_level": "unknown",
                "scene_description": response[:200],
            }

    async def quick_detect(self, frame) -> Dict[str, Any]:
        """
        Quick detection - just count people and check for threats.

        Faster than full analysis.
        """
        prompt = """Quick analysis:
- How many people?
- Any weapons visible?
- Any suspicious behavior?

JSON: {"person_count": X, "has_weapon": true/false, "is_suspicious": true/false}"""

        return await self.analyze(frame, prompt)

    async def describe_scene(self, frame) -> str:
        """Get natural language scene description."""
        prompt = """Describe this scene in 2-3 sentences. What's happening? Who is there? What are they doing?"""
        result = await self.analyze(frame, prompt)
        return result.get(
            "scene_description", result.get("raw_response", "Unable to analyze")
        )

    async def detect_threats(self, frame) -> Dict[str, Any]:
        """Dedicated threat detection."""
        prompt = """Security threat analysis:
1. Any weapons (guns, knives, bats)?
2. Any suspicious behavior (breaking in, hiding)?
3. Any unusual activity?
4. Threat level?

JSON: {"has_weapon": true/false, "suspicious_activity": "description", "threat_level": "low/medium/high", "action_recommended": "what to do"}"""

        return await self.analyze(frame, prompt)

    async def analyze_appearance(self, frame) -> Dict[str, Any]:
        """Analyze person's appearance for fashion/look questions."""
        prompt = """Analyze the person's appearance:
1. What are they wearing (clothing, colors)?
2. How do they look (mood, expression)?
3. Overall style assessment?

JSON: {"clothing": "description", "colors": ["list"], "mood": "description", "style": "assessment"}"""

        return await self.analyze(frame, prompt)

    async def find_object(self, frame, object_name: str) -> Dict[str, Any]:
        """Find specific object in frame."""
        prompt = f"""Search for "{object_name}" in this image:
1. Is {object_name} visible?
2. Where is it located?
3. What does it look like?

JSON: {"found": true/false, "location": "description", "appearance": "description"}"""

        return await self.analyze(frame, prompt)


def get_security_agent() -> SecurityAgent:
    """Get or create the Security Agent singleton."""
    global _security_agent
    if _security_agent is None:
        _security_agent = SecurityAgent()
    return _security_agent
