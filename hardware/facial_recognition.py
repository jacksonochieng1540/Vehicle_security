"""
Facial Recognition Module using OpenCV - FIXED VERSION
Handles face detection, encoding, and authentication
"""
import cv2
import numpy as np
import pickle
import os
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('hardware')


class FacialRecognitionSystem:
    """
    OpenCV-based facial recognition system for vehicle authentication
    Uses Haar Cascades for face detection and LBPH for recognition
    """
    
    def __init__(self):
        # Load Haar Cascade classifiers
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
        # FIXED: Get settings from correct location with fallbacks
        facial_config = getattr(settings, 'FACIAL_RECOGNITION_CONFIG', {})
        
        # Recognition tolerance (0.0 - 1.0, higher = more strict)
        self.recognition_tolerance = facial_config.get('RECOGNITION_TOLERANCE', 0.6)
        
        # Get directories with safe fallbacks
        self.encodings_dir = Path(facial_config.get('ENCODINGS_DIR', settings.MEDIA_ROOT / 'facial_encodings'))
        self.unauthorized_dir = Path(facial_config.get('UNAUTHORIZED_IMAGES_DIR', settings.MEDIA_ROOT / 'unauthorized_images'))
        
        # Create directories if they don't exist
        os.makedirs(self.encodings_dir, exist_ok=True)
        os.makedirs(self.unauthorized_dir, exist_ok=True)
        
        # Initialize face recognizer (LBPH - Local Binary Pattern Histogram)
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            logger.info("✅ Facial recognition system initialized (OpenCV LBPH)")
        except AttributeError:
            # cv2.face might not be available in some OpenCV builds
            logger.warning("⚠️ cv2.face.LBPHFaceRecognizer not available - using basic recognition")
            self.recognizer = None
        
        logger.info(f"📸 Recognition tolerance: {self.recognition_tolerance}")
        logger.info(f"📁 Encodings dir: {self.encodings_dir}")
        
    def detect_faces(self, image):
        """
        Detect faces in an image using Haar Cascade
        
        Args:
            image: OpenCV image (BGR format)
            
        Returns:
            List of face rectangles (x, y, w, h)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        logger.debug(f"Detected {len(faces)} face(s) in image")
        return faces
    
    def extract_face_encoding(self, image, face_rect):
        """
        Extract facial features from detected face
        
        Args:
            image: OpenCV image
            face_rect: Tuple (x, y, w, h) of face location
            
        Returns:
            Face encoding (numpy array of grayscale face)
        """
        x, y, w, h = face_rect
        face_roi = image[y:y+h, x:x+w]
        
        # Resize to standard size (200x200)
        face_roi = cv2.resize(face_roi, (200, 200))
        
        # Convert to grayscale
        gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # Apply histogram equalization for better recognition
        gray_face = cv2.equalizeHist(gray_face)
        
        return gray_face
    
    def train_face(self, image_path_or_array):
        """
        Train face from image (compatible with views.py)
        
        Args:
            image_path_or_array: Path to image file or numpy array
            
        Returns:
            Dictionary with success status and encoding
        """
        try:
            # Load image
            if isinstance(image_path_or_array, (str, Path)):
                image = cv2.imread(str(image_path_or_array))
                logger.info(f"📸 Loading image from: {image_path_or_array}")
            elif isinstance(image_path_or_array, np.ndarray):
                image = image_path_or_array
                logger.info("📸 Using provided image array")
            else:
                logger.error(f"Invalid image type: {type(image_path_or_array)}")
                return {
                    'success': False,
                    'error': 'Invalid image type',
                    'encoding': None
                }
            
            if image is None:
                logger.error("Failed to load image")
                return {
                    'success': False,
                    'error': 'Failed to load image',
                    'encoding': None
                }
            
            # Detect faces
            faces = self.detect_faces(image)
            
            if len(faces) == 0:
                logger.warning("No faces detected in image")
                return {
                    'success': False,
                    'error': 'No face detected in image. Please use a clear frontal face photo.',
                    'encoding': None
                }
            
            if len(faces) > 1:
                logger.warning(f"Multiple faces detected ({len(faces)}), using largest")
            
            # Use the largest face
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            
            logger.info(f"✅ Face detected at ({x}, {y}) with size {w}x{h}")
            
            # Extract encoding
            face_encoding = self.extract_face_encoding(image, largest_face)
            
            logger.info("✅ Face encoding extracted successfully")
            
            return {
                'success': True,
                'encoding': face_encoding,
                'face_location': largest_face,
                'num_faces': len(faces),
                'message': 'Face trained successfully'
            }
            
        except Exception as e:
            logger.error(f"Face training error: {e}")
            return {
                'success': False,
                'error': str(e),
                'encoding': None
            }
    
    def train_user_face(self, user_id, image_path=None, image_array=None):
        """
        Train the recognizer with a user's face
        
        Args:
            user_id: User ID
            image_path: Path to image file
            image_array: Or numpy array of image
            
        Returns:
            Boolean success status
        """
        logger.info(f"🔄 Training face for user ID: {user_id}")
        
        # Use the train_face method
        result = self.train_face(image_path or image_array)
        
        if result['success']:
            # Save encoding
            encoding = result['encoding']
            encoding_path = self.encodings_dir / f"user_{user_id}.pkl"
            
            with open(encoding_path, 'wb') as f:
                pickle.dump(encoding, f)
            
            logger.info(f"✅ Encoding saved to: {encoding_path}")
            return True
        else:
            logger.warning(f"❌ Face training failed: {result.get('error')}")
            return False
    
    def load_authorized_encodings(self, vehicle_id):
        """
        Load all authorized user encodings for a vehicle
        
        Returns:
            Dictionary mapping user_id to encoding
        """
        from authentication.models import User
        from vehicle_tracking.models import Vehicle
        
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            logger.error(f"Vehicle {vehicle_id} not found")
            return {}
        
        authorized_users = User.objects.filter(
            vehicle=vehicle,
            is_authorized_driver=True
        )
        
        encodings = {}
        for user in authorized_users:
            encoding_path = self.encodings_dir / f"user_{user.id}.pkl"
            if encoding_path.exists():
                with open(encoding_path, 'rb') as f:
                    encodings[user.id] = pickle.load(f)
                logger.debug(f"Loaded encoding for user {user.id}")
            else:
                logger.warning(f"No encoding file for user {user.id}")
        
        logger.info(f"Loaded {len(encodings)} authorized encodings for vehicle {vehicle_id}")
        return encodings
    
    def authenticate_face(self, image, vehicle_id):
        """
        Authenticate a face against authorized users
        
        Args:
            image: OpenCV image or path to image
            vehicle_id: Vehicle ID to check authorization for
            
        Returns:
            Tuple (is_authenticated, user_id, confidence_score, face_image)
        """
        logger.info(f"🔍 Authenticating face for vehicle {vehicle_id}")
        
        # Load image if path is provided
        if isinstance(image, (str, Path)):
            image = cv2.imread(str(image))
        
        if image is None:
            logger.error("Failed to load image for authentication")
            return False, None, 0.0, None
        
        # Detect faces
        faces = self.detect_faces(image)
        
        if len(faces) == 0:
            logger.warning("No faces detected in authentication image")
            return False, None, 0.0, None
        
        # Use the largest face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face
        
        # Extract face encoding
        face_encoding = self.extract_face_encoding(image, largest_face)
        
        # Load authorized encodings
        authorized_encodings = self.load_authorized_encodings(vehicle_id)
        
        if not authorized_encodings:
            logger.warning("No authorized users for this vehicle")
            return False, None, 0.0, self._extract_face_image(image, largest_face)
        
        # Compare with each authorized user
        best_match_user = None
        best_confidence = float('inf')
        
        for user_id, encoding in authorized_encodings.items():
            try:
                # Ensure both arrays have the same shape
                if face_encoding.shape != encoding.shape:
                    logger.warning(f"Shape mismatch for user {user_id}")
                    continue
                    
                # Calculate difference (using Euclidean distance)
                diff = np.linalg.norm(face_encoding - encoding)
                
                logger.debug(f"User {user_id}: distance = {diff}")
                
                if diff < best_confidence:
                    best_confidence = diff
                    best_match_user = user_id
            except Exception as e:
                logger.error(f"Error comparing with user {user_id}: {e}")
                continue
        
        # Normalize confidence to 0-1 range (lower distance = better match)
        # Typical distance range: 0-10000, we invert so higher confidence = better
        normalized_confidence = max(0, 1 - (best_confidence / 10000))
        
        logger.info(f"Best match: User {best_match_user}, Confidence: {normalized_confidence:.2f}")
        
        # Check if confidence meets threshold
        is_authenticated = normalized_confidence >= self.recognition_tolerance
        
        if is_authenticated:
            logger.info(f"✅ AUTHENTICATED - User {best_match_user}")
        else:
            logger.warning(f"❌ UNAUTHORIZED - Confidence {normalized_confidence:.2f} < {self.recognition_tolerance}")
        
        # Extract face image
        face_image = self._extract_face_image(image, largest_face)
        
        return is_authenticated, best_match_user, normalized_confidence, face_image
    
    def _extract_face_image(self, image, face_rect):
        """Extract face region as a separate image"""
        x, y, w, h = face_rect
        # Add padding
        padding = 20
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(image.shape[1], x + w + padding)
        y2 = min(image.shape[0], y + h + padding)
        
        face_image = image[y1:y2, x1:x2]
        return face_image
    
    def save_unauthorized_image(self, image, vehicle_id):
        """
        Save image of unauthorized access attempt
        
        Returns:
            Path to saved image
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"unauthorized_{vehicle_id}_{timestamp}.jpg"
        filepath = self.unauthorized_dir / filename
        
        cv2.imwrite(str(filepath), image)
        logger.info(f"💾 Saved unauthorized image: {filepath}")
        return filepath
    
    def capture_from_camera(self, camera_index=0):
        """
        Capture image from camera
        
        Args:
            camera_index: Camera device index
            
        Returns:
            OpenCV image or None
        """
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            logger.error(f"Failed to open camera {camera_index}")
            return None
        
        # Allow camera to warm up
        import time
        time.sleep(0.5)
        
        # Capture frame
        ret, frame = cap.read()
        
        cap.release()
        
        if ret:
            logger.info("✅ Image captured from camera")
            return frame
        
        logger.error("Failed to capture frame from camera")
        return None


# Singleton instance
_facial_recognition_system = None

def get_facial_recognition_system():
    """Get or create facial recognition system instance"""
    global _facial_recognition_system
    if _facial_recognition_system is None:
        _facial_recognition_system = FacialRecognitionSystem()
    return _facial_recognition_system