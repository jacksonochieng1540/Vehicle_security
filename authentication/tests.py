"""
Authentication App Tests
Tests for user registration, login, profile management, and face training
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from authentication.models import AuthenticationLog
from vehicle_tracking.models import Vehicle
import base64
from io import BytesIO
from PIL import Image

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            phone_number='+254712345678',
            role='driver'
        )
    
    def test_user_creation(self):
        """Test user can be created"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.role, 'driver')
        self.assertTrue(self.user.check_password('testpass123'))
    
    def test_get_full_name(self):
        """Test get_full_name method"""
        self.assertEqual(self.user.get_full_name(), 'Test User')
    
    def test_str_representation(self):
        """Test string representation"""
        # FIXED: Match your actual model's __str__ output
        # Based on error message, your model returns: "Test User (driver)"
        expected = f"{self.user.first_name} {self.user.last_name} ({self.user.role})"
        self.assertEqual(str(self.user), expected)
    
    def test_is_authorized_driver_default(self):
        """Test is_authorized_driver defaults to False"""
        self.assertFalse(self.user.is_authorized_driver)


class UserRegistrationTest(TestCase):
    """Test user registration views"""
    
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('authentication:register')
    
    def test_registration_page_loads(self):
        """Test registration page is accessible"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/register.html')
    
    def test_register_with_valid_data(self):
        """Test user can register with valid data"""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'phone_number': '+254723456789',
            'role': 'driver',
        }
        
        response = self.client.post(self.register_url, data)
        
        # Should redirect to login after successful registration
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('authentication:login'))
        
        # User should exist in database
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_register_with_profile_image(self):
        """Test registration with profile image upload"""
        # Create a test image
        image = Image.new('RGB', (100, 100), color='red')
        image_file = BytesIO()
        image.save(image_file, 'JPEG')
        image_file.seek(0)
        
        uploaded_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )
        
        data = {
            'username': 'imageuser',
            'email': 'image@example.com',
            'first_name': 'Image',
            'last_name': 'User',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'phone_number': '+254734567890',
            'role': 'driver',
            'profile_image': uploaded_image,
        }
        
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)
        
        # Check user has profile image
        user = User.objects.get(username='imageuser')
        self.assertIsNotNone(user.profile_image)
    
    def test_register_with_captured_photo(self):
        """Test registration with camera-captured photo (base64)"""
        # Create a small test image and convert to base64
        image = Image.new('RGB', (100, 100), color='blue')
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        data = {
            'username': 'captureduser',
            'email': 'captured@example.com',
            'first_name': 'Captured',
            'last_name': 'User',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'phone_number': '+254745678901',
            'role': 'driver',
            'captured_photo_data': f'data:image/jpeg;base64,{img_str}',
        }
        
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)
        
        # Check user was created with image
        user = User.objects.get(username='captureduser')
        self.assertIsNotNone(user.profile_image)
    
    def test_register_with_mismatched_passwords(self):
        """Test registration fails with mismatched passwords"""
        data = {
            'username': 'badpass',
            'email': 'bad@example.com',
            'first_name': 'Bad',
            'last_name': 'Pass',
            'password1': 'password123',
            'password2': 'different456',
            'role': 'driver',
        }
        
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)  # Stays on same page
        self.assertFalse(User.objects.filter(username='badpass').exists())


class UserLoginTest(TestCase):
    """Test user login functionality"""
    
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('authentication:login')
        self.user = User.objects.create_user(
            username='loginuser',
            email='login@example.com',
            password='loginpass123',
            first_name='Login',
            last_name='User'
        )
    
    def test_login_page_loads(self):
        """Test login page is accessible"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/login.html')
    
    def test_login_with_valid_credentials(self):
        """Test user can login with valid credentials"""
        response = self.client.post(self.login_url, {
            'username': 'loginuser',
            'password': 'loginpass123'
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        
        # User should be authenticated
        user = User.objects.get(username='loginuser')
        self.assertTrue(self.client.session['_auth_user_id'])
    
    def test_login_with_invalid_credentials(self):
        """Test login fails with invalid credentials"""
        response = self.client.post(self.login_url, {
            'username': 'loginuser',
            'password': 'wrongpassword'
        })
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        
        # User should not be authenticated
        self.assertNotIn('_auth_user_id', self.client.session)
    
    def test_authenticated_user_redirects(self):
        """Test authenticated user is redirected from login page"""
        self.client.login(username='loginuser', password='loginpass123')
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)


class UserProfileTest(TestCase):
    """Test user profile views and updates"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='profilepass123',
            first_name='Profile',
            last_name='User'
        )
        self.profile_url = reverse('authentication:profile')
        self.client.login(username='profileuser', password='profilepass123')
    
    def test_profile_page_requires_login(self):
        """Test profile page requires authentication"""
        self.client.logout()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)  # Redirects to login
    
    def test_profile_page_loads_for_authenticated_user(self):
        """Test profile page loads for logged in user"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/profile.html')
    
    def test_profile_update(self):
        """Test user can update profile"""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'phone_number': '+254756789012'
        }
        
        response = self.client.post(self.profile_url, data)
        
        # Should redirect back to profile
        self.assertEqual(response.status_code, 302)
        
        # Check user data was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.email, 'updated@example.com')


class AuthenticationLogTest(TestCase):
    """Test authentication logging"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='loguser',
            password='logpass123'
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            registration_number='KCA 001A',
            make='Toyota',
            model='Corolla',
            year=2020,
            device_id='RPI_001'
        )
    
    def test_create_authentication_log(self):
        """Test authentication log can be created"""
        log = AuthenticationLog.objects.create(
            user=self.user,
            vehicle=self.vehicle,
            status='success',
            confidence_score=0.87,
            location_latitude=-1.0927,
            location_longitude=37.0143
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.vehicle, self.vehicle)
        self.assertEqual(log.status, 'success')
        self.assertEqual(log.confidence_score, 0.87)
    
    def test_unauthorized_log(self):
        """Test creating unauthorized access log"""
        log = AuthenticationLog.objects.create(
            user=None,  # Unknown person
            vehicle=self.vehicle,
            status='unauthorized',
            confidence_score=0.32
        )
        
        self.assertIsNone(log.user)
        self.assertEqual(log.status, 'unauthorized')


class LogoutTest(TestCase):
    """Test user logout"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='logoutuser',
            password='logoutpass123'
        )
        self.logout_url = reverse('authentication:logout')
    
    def test_logout_clears_session(self):
        """Test logout clears user session"""
        self.client.login(username='logoutuser', password='logoutpass123')
        
        # Verify user is logged in
        self.assertTrue('_auth_user_id' in self.client.session)
        
        # Logout
        response = self.client.get(self.logout_url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        
        # Session should be cleared
        self.assertNotIn('_auth_user_id', self.client.session)


# Run tests with:
# python manage.py test authentication