"""
Authentication Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .models import User, AuthenticationLog
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm


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
    """Handle user registration"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please log in.')
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
    """View and edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('authentication:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    # Get recent authentication logs for this user
    recent_logs = AuthenticationLog.objects.filter(user=request.user)[:10]
    
    context = {
        'form': form,
        'recent_logs': recent_logs,
    }
    return render(request, 'authentication/profile.html', context)


@login_required
def authentication_history(request):
    """View authentication history"""
    if request.user.vehicle:
        logs = AuthenticationLog.objects.filter(vehicle=request.user.vehicle)
    else:
        logs = AuthenticationLog.objects.filter(user=request.user)
    
    context = {
        'logs': logs,
    }
    return render(request, 'authentication/history.html', context)