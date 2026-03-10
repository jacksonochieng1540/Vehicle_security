"""
Authentication Views - FIXED VERSION
Better error handling and safer settings access
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.files.base import ContentFile
from .models import User, AuthenticationLog
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm
import base64
import os
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                next_url = request.GET.get('next', 'dashboard:home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'authentication/login.html', {'form': form})


@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    Handle user registration with support for both file upload and live camera capture.
    Automatically trains facial recognition after registration.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        
        if form.is_valid():
            user = form.save(commit=False)
            
            # Check if photo was captured via live camera
            captured_photo_data = request.POST.get('captured_photo_data')
            
            if captured_photo_data:
                try:
                    # Decode base64 image
                    format, imgstr = captured_photo_data.split(';base64,')
                    ext = format.split('/')[-1]
                    image_data = base64.b64decode(imgstr)
                    filename = f'captured_{user.username}.{ext}'
                    user.profile_image = ContentFile(image_data, name=filename)
                    logger.info(f"📸 Face captured from camera for user: {user.username}")
                except Exception as e:
                    logger.error(f"Failed to process captured photo: {e}")
                    messages.error(request, f'Failed to process captured photo: {str(e)}')
                    return render(request, 'authentication/register.html', {'form': form})
            
            # Save user to database FIRST
            user.save()
            logger.info(f"✅ User account created: {user.username}")
            
            # Try to auto-train facial recognition if profile image exists
            if user.profile_image:
                face_training_success = train_user_face(user)
                
                if face_training_success:
                    messages.success(
                        request, 
                        f'✅ Registration successful! '
                        f'Welcome, {user.get_full_name()}! '
                        f'Your face has been registered.'
                    )
                else:
                    messages.warning(
                        request,
                        f'✅ Account created! '
                        f'⚠️ Face registration needs a clearer photo. '
                        f'Please update in your profile.'
                    )
            else:
                messages.success(
                    request, 
                    f'✅ Account created! Please add a face photo in your profile.'
                )
            
            return redirect('authentication:login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'authentication/register.html', {'form': form})


def train_user_face(user):
    """
    Train facial recognition for a user
    
    Returns:
        bool: True if training succeeded, False otherwise
    """
    try:
        logger.info(f"🔄 Starting face training for user: {user.username}")
        
        from hardware.facial_recognition import get_facial_recognition_system
        
        try:
            facial_system = get_facial_recognition_system(simulated=False)
        except Exception:
            logger.warning("Using simulated facial recognition")
            facial_system = get_facial_recognition_system(simulated=True)
        
        image_path = user.profile_image.path
        
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return False
        
        result = facial_system.train_face(image_path)
        
        if result and result.get('success'):
            encoding = result.get('encoding')
            if encoding is not None:
                import pickle
                user.facial_encoding = pickle.dumps(encoding)
                user.save()
                logger.info(f"✅ Face training successful: {user.username}")
                return True
            else:
                logger.warning(f"No encoding returned: {user.username}")
                return False
        else:
            error_msg = result.get('error', 'Unknown') if result else 'No result'
            logger.warning(f"Face training failed: {user.username}: {error_msg}")
            return False
            
    except ImportError as e:
        logger.warning(f"Facial recognition not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Face training error: {user.username}: {e}")
        return False


@login_required
def logout_view(request):
    """Handle user logout"""
    username = request.user.username
    logout(request)
    messages.info(request, f'Logged out. Goodbye, {username}!')
    return redirect('authentication:login')


@login_required
def profile_view(request):
    """View and edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            old_profile_image = request.user.profile_image
            user = form.save()
            
            if user.profile_image and user.profile_image != old_profile_image:
                success = train_user_face(user)
                
                if success:
                    messages.success(request, '✅ Profile and face updated!')
                else:
                    messages.warning(request, '✅ Profile updated! ⚠️ Face needs clearer photo.')
            else:
                messages.success(request, '✅ Profile updated!')
            
            return redirect('authentication:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    recent_logs = AuthenticationLog.objects.filter(user=request.user).order_by('-timestamp')[:10]
    face_trained = bool(request.user.facial_encoding)
    
    context = {
        'form': form,
        'recent_logs': recent_logs,
        'face_trained': face_trained,
    }
    return render(request, 'authentication/profile.html', context)


@login_required
def authentication_history(request):
    """View authentication history"""
    if request.user.vehicle:
        logs = AuthenticationLog.objects.filter(vehicle=request.user.vehicle).order_by('-timestamp')
    else:
        logs = AuthenticationLog.objects.filter(user=request.user).order_by('-timestamp')
    
    return render(request, 'authentication/history.html', {'logs': logs})