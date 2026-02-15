"""
Facial Recognition Module using OpenCV
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


class FacialRecognitionSystem:
    """
    OpenCV-based facial recognition system for vehicle authentication
    """
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        self.recognition_tolerance = settings.HARDWARE_CONFIG['RECOGNITION_TOLERANCE']
        self.encodings_dir = settings.FACIAL_RECOGNITION_CONFIG['ENCODINGS_DIR']
        self.unauthorized_dir = settings.FACIAL_RECOGNITION_CONFIG['UNAUTHORIZED_IMAGES_DIR']
        
        # Create directories if they don't exist
        os.makedirs(self.encodings_dir, exist_ok=True)
        os.makedirs(self.unauthorized_dir, exist_ok=True)
        
        # Initialize face recognizer
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        
    def detect_faces(self, image):
        """
        Detect faces in an image
        
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
        return faces
    
    def extract_face_encoding(self, image, face_rect):
        """
        Extract facial features from detected face
        
        Args:
            image: OpenCV image
            face_rect: Tuple (x, y, w, h) of face location
            
        Returns:
            Face encoding (numpy array)
        """
        x, y, w, h = face_rect
        face_roi = image[y:y+h, x:x+w]
        
        # Resize to standard size
        face_roi = cv2.resize(face_roi, (200, 200))
        
        # Convert to grayscale
        gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # Apply histogram equalization for better recognition
        gray_face = cv2.equalizeHist(gray_face)
        
        return gray_face
    
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
        # Load image
        if image_path:
            image = cv2.imread(str(image_path))
        elif image_array is not None:
            image = image_array
        else:
            return False
        
        if image is None:
            return False
        
        # Detect faces
        faces = self.detect_faces(image)
        
        if len(faces) == 0:
            return False
        
        # Use the largest face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        
        # Extract encoding
        face_encoding = self.extract_face_encoding(image, largest_face)
        
        # Save encoding
        encoding_path = self.encodings_dir / f"user_{user_id}.pkl"
        with open(encoding_path, 'wb') as f:
            pickle.dump(face_encoding, f)
        
        return True
    
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
        # Load image if path is provided
        if isinstance(image, (str, Path)):
            image = cv2.imread(str(image))
        
        if image is None:
            return False, None, 0.0, None
        
        # Detect faces
        faces = self.detect_faces(image)
        
        if len(faces) == 0:
            return False, None, 0.0, None
        
        # Use the largest face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face
        
        # Extract face encoding
        face_encoding = self.extract_face_encoding(image, largest_face)
        
        # Load authorized encodings
        authorized_encodings = self.load_authorized_encodings(vehicle_id)
        
        if not authorized_encodings:
            # No authorized users
            return False, None, 0.0, self._extract_face_image(image, largest_face)
        
        # Compare with each authorized user
        best_match_user = None
        best_confidence = float('inf')
        
        for user_id, encoding in authorized_encodings.items():
            # Calculate difference (using simple Euclidean distance)
            try:
                # Ensure both arrays have the same shape
                if face_encoding.shape != encoding.shape:
                    continue
                    
                diff = np.linalg.norm(face_encoding - encoding)
                
                if diff < best_confidence:
                    best_confidence = diff
                    best_match_user = user_id
            except Exception as e:
                print(f"Error comparing encodings: {e}")
                continue
        
        # Normalize confidence to 0-1 range (lower is better, so invert)
        normalized_confidence = max(0, 1 - (best_confidence / 10000))
        
        # Check if confidence meets threshold
        is_authenticated = normalized_confidence >= self.recognition_tolerance
        
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
            return None
        
        # Allow camera to warm up
        import time
        time.sleep(0.5)
        
        # Capture frame
        ret, frame = cap.read()
        
        cap.release()
        
        if ret:
            return frame
        return None


# Singleton instance
_facial_recognition_system = None

def get_facial_recognition_system():
    """Get or create facial recognition system instance"""
    global _facial_recognition_system
    if _facial_recognition_system is None:
        _facial_recognition_system = FacialRecognitionSystem()
    return _facial_recognition_system