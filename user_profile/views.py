from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout, login as auth_login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
import django_cas_ng.views
from .forms import UserUpdateForm, UserProfileUpdateForm

def login_view(request):
    """Menangani login: Mock login untuk lokal (DEBUG=True) dan CAS SSO UI untuk produksi."""
    if settings.DEBUG:
        user, created = User.objects.get_or_create(username="mahasiswa_ui_test")
        
        # Tentukan backend secara eksplisit untuk menghindari error multiple backends di Django
        backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user, backend=backend)
        
        messages.success(request, 'Berhasil login menggunakan akun uji coba lokal!')
        return redirect('user_profile:profile')
    
    return django_cas_ng.views.LoginView.as_view()(request)

def logout_view(request):
    """Menangani proses keluar akun."""
    if settings.DEBUG:
        auth_logout(request)
        messages.info(request, 'Anda telah keluar dari sesi lokal.')
        return redirect('/')
    return django_cas_ng.views.LogoutView.as_view()(request)

@login_required
def profile_view(request):
    """Menampilkan dan memperbarui profil serta preferensi target kesehatan."""
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = UserProfileUpdateForm(request.POST, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Profil dan preferensi kesehatan kamu berhasil diperbarui!')
            return redirect('user_profile:profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = UserProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form,
    }
    return render(request, 'user_profile/profile.html', context)