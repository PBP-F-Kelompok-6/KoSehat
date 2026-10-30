from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, UserProfileUpdateForm
from .models import UserProfile

def register_view(request):
    """Menangani pendaftaran akun baru & otomatis login setelah berhasil."""
    if request.user.is_authenticated:
        return redirect('user_profile:profile')
        
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            
            auth_login(request, user)
            messages.success(request, 'Akun berhasil dibuat dan kamu langsung masuk!')
            return redirect('user_profile:profile')
    else:
        form = UserRegisterForm()
    
    return render(request, 'user_profile/register.html', {'form': form})

def login_view(request):
    """Menangani login manual menggunakan username dan password yang sudah dibuat."""
    if request.user.is_authenticated:
        return redirect('user_profile:profile')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'Selamat datang kembali, {user.username}!')
            return redirect('user_profile:profile')
        else:
            messages.error(request, 'Username atau password salah. Silakan coba lagi.')
    else:
        form = AuthenticationForm()
        
    return render(request, 'user_profile/login.html', {'form': form})

def logout_view(request):
    """Menangani log out secara bersih untuk mencegah bug sesi tertinggal."""
    auth_logout(request)
    request.session.flush()
    messages.info(request, 'Kamu telah berhasil keluar.')
    return redirect('user_profile:login')

@login_required
def profile_view(request):
    """Menampilkan dan memproses pengisian profil serta target kesehatan."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = UserProfileUpdateForm(request.POST, instance=profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Profil dan target kesehatan berhasil diperbarui!')
            return redirect('user_profile:profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = UserProfileUpdateForm(instance=profile)

    context = {
        'u_form': u_form,
        'p_form': p_form,
    }
    return render(request, 'user_profile/profile.html', context)