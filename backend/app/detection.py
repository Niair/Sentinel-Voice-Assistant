"""
Object Detection Module using YOLO
Fast, accurate detection for monitoring system
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Try to import ultralytics (YOLO)
try:
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("⚠️ YOLO not installed. Install with: pip install ultralytics")


class ObjectDetector:
    """
    YOLO-based object detector for camera monitoring.

    Features:
    - Fast detection (30+ FPS on GPU, 10+ FPS on CPU)
    - Multiple object classes (person, car, dog, etc.)
    - Configurable confidence threshold
    - Tracks objects across frames
    """

    # Object classes we're interested in for security monitoring
    SECURITY_CLASSES = {
        0: "person",
        1: "bicycle",
        2: "car",
        3: "motorcycle",
        4: "airplane",
        5: "bus",
        6: "train",
        7: "truck",
        8: "boat",
        16: "dog",
        17: "horse",
        18: "sheep",
        19: "cow",
        20: "elephant",
        21: "bear",
        22: "zebra",
        23: "giraffe",
    }

    def __init__(self, model_name: str = "yolov8s.pt", confidence: float = 0.5):
        """
        Initialize YOLO detector

        Args:
            model_name: YOLO model to use
                - yolov8n.pt: Nano (fastest, ~37 FPS, 3.2 MB)
                - yolov8s.pt: Small (balanced, ~26 FPS, 11.4 MB) ⭐ RECOMMENDED
                - yolov8m.pt: Medium (more accurate, ~15 FPS, 25.9 MB)
            confidence: Minimum confidence threshold (0.0 - 1.0)
        """
        self.model_name = model_name
        self.confidence = confidence
        self.model = None
        self._initialized = False

        if not YOLO_AVAILABLE:
            logger.error("❌ YOLO not available. Detection will not work.")
            return

        try:
            self._load_model()
        except Exception as e:
            logger.error(f"❌ Failed to load YOLO model: {e}")

    def _load_model(self):
        """Load YOLO model"""
        logger.info(f"🤖 Loading YOLO model: {self.model_name}")

        # Download model if not exists
        model_path = self.model_name
        if not os.path.exists(model_path):
            logger.info(f"📥 Downloading {self.model_name}...")

        self.model = YOLO(model_path)
        self._initialized = True
        logger.info(f"✅ YOLO model loaded successfully")

    def detect(self, frame) -> List[Dict[str, Any]]:
        """
        Detect objects in frame

        Args:
            frame: OpenCV frame (numpy array)

        Returns:
            List of detections with class, confidence, and bounding box
        """
        if not self._initialized or self.model is None:
            logger.warning("⚠️ Detector not initialized")
            return []

        try:
            # Run inference
            results = self.model(frame, verbose=False)

            # Parse results
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])

                    # Filter by confidence
                    if conf < self.confidence:
                        continue

                    # Get class name
                    class_name = self.SECURITY_CLASSES.get(cls_id, f"class_{cls_id}")

                    # Get bounding box
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                    detections.append(
                        {
                            "class": class_name,
                            "class_id": cls_id,
                            "confidence": round(conf, 3),
                            "bbox": {
                                "x1": int(x1),
                                "y1": int(y1),
                                "x2": int(x2),
                                "y2": int(y2),
                            },
                        }
                    )

            return detections

        except Exception as e:
            logger.error(f"❌ Detection error: {e}")
            return []

    def detect_security_threats(self, frame) -> Dict[str, Any]:
        """
        Specialized detection for security monitoring

        Returns:
            Dictionary with threat assessment
        """
        detections = self.detect(frame)

        # Analyze detections
        persons = [d for d in detections if d["class"] == "person"]
        vehicles = [
            d for d in detections if d["class"] in ["car", "truck", "bus", "motorcycle"]
        ]
        animals = [d for d in detections if d["class"] in ["dog", "cat"]]

        # Determine threat level
        threat_level = "none"
        if persons:
            threat_level = "low"  # Person detected
        if len(persons) > 2:
            threat_level = "medium"  # Multiple people
        if vehicles and persons:
            threat_level = "medium"  # Vehicle + person

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "threat_level": threat_level,
            "total_detections": len(detections),
            "persons": persons,
            "vehicles": vehicles,
            "animals": animals,
            "all_detections": detections,
        }

    def is_person_detected(self, frame) -> bool:
        """Quick check if person is in frame"""
        detections = self.detect(frame)
        return any(d["class"] == "person" for d in detections)

    def get_status(self) -> Dict[str, Any]:
        """Get detector status"""
        return {
            "initialized": self._initialized,
            "model": self.model_name,
            "confidence_threshold": self.confidence,
            "yolo_available": YOLO_AVAILABLE,
        }


# Singleton instance
detector = ObjectDetector()
