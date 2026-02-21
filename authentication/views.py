"""
Authentication Views
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
            
            # 🔥 NEW: Check if photo was captured via live camera
            captured_photo_data = request.POST.get('captured_photo_data')
            
            if captured_photo_data:
                try:
                    # Decode base64 image
                    # Format: "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
                    format, imgstr = captured_photo_data.split(';base64,')
                    ext = format.split('/')[-1]  # Extract extension (jpeg, png, etc.)
                    
                    # Decode base64 string to bytes
                    image_data = base64.b64decode(imgstr)
                    
                    # Create Django file from bytes
                    filename = f'captured_{user.username}.{ext}'
                    user.profile_image = ContentFile(image_data, name=filename)
                    
                    messages.info(request, '📸 Face captured from camera successfully!')
                    
                except Exception as e:
                    messages.error(request, f'Failed to process captured photo: {str(e)}')
                    return render(request, 'authentication/register.html', {'form': form})
            
            # Save user to database
            user.save()
            
            # 🔥 NEW: Auto-train facial recognition if profile image exists
            if user.profile_image:
                try:
                    from hardware.facial_recognition import get_facial_recognition_system
                    
                    facial_system = get_facial_recognition_system()
                    
                    # Get the full path to the uploaded image
                    image_path = user.profile_image.path
                    
                    # Train the face encoding
                    success = facial_system.train_user_face(
                        user_id=user.id,
                        image_path=image_path
                    )
                    
                    if success:
                        messages.success(
                            request, 
                            f'✅ Account created successfully! '
                            f'Face registered for {user.get_full_name()}. '
                            f'You can now authenticate at vehicles.'
                        )
                    else:
                        messages.warning(
                            request,
                            f'⚠️ Account created but face detection failed. '
                            f'No clear face found in the image. '
                            f'Please update your profile with a clearer frontal face photo.'
                        )
                    
                except ImportError:
                    # Facial recognition module not available (dev environment)
                    messages.success(
                        request,
                        'Registration successful! Please log in. '
                        '(Face training will be done by admin)'
                    )
                except Exception as e:
                    # Face training failed but account was created
                    messages.warning(
                        request,
                        f'⚠️ Account created but face training failed: {str(e)}. '
                        f'Please contact admin to train your face manually.'
                    )
            else:
                messages.success(
                    request, 
                    'Registration successful! Please log in. '
                    '(Note: Face photo is required for vehicle authentication)'
                )
            
            return redirect('authentication:login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'authentication/register.html', {'form': form})


@login_required
def logout_view(request):
    """Handle user logout"""
    username = request.user.username
    logout(request)
    messages.info(request, f'You have been logged out. Goodbye, {username}!')
    return redirect('authentication:login')


@login_required
def profile_view(request):
    """
    View and edit user profile.
    Supports updating face photo and retraining facial recognition.
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            # Check if profile image was updated
            old_profile_image = request.user.profile_image
            user = form.save()
            
            # 🔥 NEW: Retrain face if profile image changed
            if user.profile_image and user.profile_image != old_profile_image:
                try:
                    from hardware.facial_recognition import get_facial_recognition_system
                    
                    facial_system = get_facial_recognition_system()
                    success = facial_system.train_user_face(
                        user_id=user.id,
                        image_path=user.profile_image.path
                    )
                    
                    if success:
                        messages.success(
                            request, 
                            '✅ Profile updated and face retrained successfully!'
                        )
                    else:
                        messages.warning(
                            request,
                            '⚠️ Profile updated but face detection failed. '
                            'Please upload a clearer frontal face photo.'
                        )
                except Exception as e:
                    messages.warning(
                        request,
                        f'Profile updated but face retraining failed: {str(e)}'
                    )
            else:
                messages.success(request, 'Profile updated successfully!')
            
            return redirect('authentication:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    # Get recent authentication logs for this user
    recent_logs = AuthenticationLog.objects.filter(user=request.user).order_by('-timestamp')[:10]
    
    # 🔥 NEW: Check if face is trained
    face_trained = False
    if request.user.profile_image:
        try:
            from django.conf import settings
            encodings_dir = settings.FACIAL_RECOGNITION_CONFIG['ENCODINGS_DIR']
            encoding_path = encodings_dir / f"user_{request.user.id}.pkl"
            face_trained = encoding_path.exists()
        except Exception:
            pass
    
    context = {
        'form': form,
        'recent_logs': recent_logs,
        'face_trained': face_trained,  # Pass to template
    }
    return render(request, 'authentication/profile.html', context)


@login_required
def authentication_history(request):
    """View authentication history"""
    if request.user.vehicle:
        logs = AuthenticationLog.objects.filter(vehicle=request.user.vehicle).order_by('-timestamp')
    else:
        logs = AuthenticationLog.objects.filter(user=request.user).order_by('-timestamp')
    
    context = {
        'logs': logs,
    }
    return render(request, 'authentication/history.html', context)