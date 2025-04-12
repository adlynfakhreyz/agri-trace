import base64
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
from .models import Buyer, Farmer, Merchant, Seller, User
from django.contrib import messages
from .forms import CustomUserCreationForm

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_2fa_enabled:
                # Store user ID in session for 2FA verification step
                request.session['2fa_user_id'] = user.id
                return redirect('verify_2fa')
            else:
                login(request, user)
                return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password")
            return redirect('login')
    
    return render(request, 'authentication/login.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log the user in
            login(request, user)
            
            # Generate OTP secret (but don't enable 2FA yet)
            user.generate_otp_secret()
            
            # Redirect to 2FA setup
            return redirect('setup_2fa')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'authentication/register.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def setup_2fa(request):
    user = request.user
    
    if request.method == 'POST':
        totp = pyotp.TOTP(user.otp_secret)
        if totp.verify(request.POST.get('verification_code', '')):
            user.is_2fa_enabled = True
            user.save()
            messages.success(request, "Two-factor authentication successfully enabled!")
            return redirect('dashboard')  # Changed from select_role to dashboard
        else:
            messages.error(request, "Invalid verification code. Please try again.")
    
    # Generate the provisioning URI
    otp_uri = pyotp.totp.TOTP(user.otp_secret).provisioning_uri(
        name=user.email,
        issuer_name="AgriTrace"
    )
    
    # Generate QR code as PNG
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(otp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'authentication/setup_2fa.html', {
        'qr_code_b64': qr_code_b64,
        'otp_secret': user.otp_secret
    })

def verify_2fa(request):
    if '2fa_user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session['2fa_user_id']
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        totp = pyotp.TOTP(user.otp_secret)
        if totp.verify(request.POST.get('verification_code', '')):
            # Clear the session and log the user in
            del request.session['2fa_user_id']
            login(request, user)
            return redirect('dashboard')  # Removed role selection check
        else:
            messages.error(request, "Invalid verification code. Please try again.")
    
    return render(request, 'authentication/verify_2fa.html')