from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from .forms import CustomSignUpForm, CustomSignInForm
from .models import User
import json
import random
import threading
from datetime import timedelta
from django.contrib.auth import authenticate, login, get_user_model
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from admin_panel.utils import send_sms_task










User = get_user_model()


def _normalize_bd_phone(phone: str) -> str:
    clean = "".join(ch for ch in str(phone or "") if ch.isdigit())

    if clean.startswith("01"):
        return "88" + clean
    if clean.startswith("1"):
        return "880" + clean
    if clean.startswith("8801"):
        return clean
    if clean.startswith("88") and len(clean) >= 13 and clean[2:4] == "01":
        return clean

    return clean

def _login_otp_cache_key(phone_norm: str) -> str:
    return f"login_otp:{phone_norm}"


@require_POST
def send_login_otp_view(request):
    try:
        data = json.loads(request.body or "{}")
        phone = (data.get("phone") or "").strip()

        if not phone:
            return JsonResponse({"success": False, "error": "Phone number is required."}, status=400)

        phone_norm = _normalize_bd_phone(phone)

        if not phone_norm.startswith("8801") or len(phone_norm) != 13:
            return JsonResponse({"success": False, "error": "Invalid BD phone number."}, status=400)

        User = get_user_model()

        # Your DB likely stores local format (01XXXXXXXXX) or normalized format.
        # We check both safely.
        local_phone = phone_norm[2:]  # 8801XXXXXXXXX -> 01XXXXXXXXX

        user = User.objects.filter(phone_number__in=[phone_norm, local_phone]).first()
        if not user:
            return JsonResponse({"success": False, "error": "No account found with this phone number."}, status=404)

        otp = f"{random.randint(0, 999999):06d}"
        ttl_seconds = 5 * 60  # OTP valid for 5 minutes

        # Resend cooldown logic (1 minute)
        existing = cache.get(_login_otp_cache_key(phone_norm)) or {}
        last_sent_at = existing.get("last_sent_ts")
        now_ts = int(timezone.now().timestamp())

        if last_sent_at and (now_ts - int(last_sent_at)) < 60:
            remaining = 60 - (now_ts - int(last_sent_at))
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Please wait {remaining}s before resending OTP.",
                    "retry_after": remaining
                },
                status=429
            )

        cache.set(
            _login_otp_cache_key(phone_norm),
            {
                "otp": otp,
                "phone": phone_norm,
                "user_id": user.id,
                "created_at": timezone.now().isoformat(),
                "attempts": 0,
                "last_sent_ts": now_ts,
                "verified": False,
            },
            timeout=ttl_seconds
        )

        msg = f"MK Shipping Login OTP: {otp}. Valid for 5 minutes."
        send_sms_task(phone_norm, msg)

        return JsonResponse(
            {
                "success": True,
                "message": f"OTP sent to {phone_norm}.",
                "expires_in": ttl_seconds,
                "resend_in": 60
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    
@require_POST
def verify_login_otp_view(request):
    try:
        data = json.loads(request.body or "{}")
        phone = (data.get("phone") or "").strip()
        otp_input = (data.get("otp") or "").strip()
        remember_me = bool(data.get("remember_me"))

        if not phone or not otp_input:
            return JsonResponse({"success": False, "error": "Phone and OTP are required."}, status=400)

        phone_norm = _normalize_bd_phone(phone)

        payload = cache.get(_login_otp_cache_key(phone_norm))
        if not isinstance(payload, dict):
            return JsonResponse({"success": False, "error": "OTP expired. Please request again."}, status=400)

        payload["attempts"] = int(payload.get("attempts") or 0) + 1
        if payload["attempts"] > 5:
            cache.delete(_login_otp_cache_key(phone_norm))
            return JsonResponse({"success": False, "error": "Too many attempts. Please request a new OTP."}, status=429)

        if str(payload.get("otp")) != otp_input:
            cache.set(_login_otp_cache_key(phone_norm), payload, timeout=5 * 60)
            return JsonResponse({"success": False, "error": "Invalid OTP. Please try again."}, status=400)

        # OTP correct -> log user in NOW
        User = get_user_model()
        user_id = payload.get("user_id")
        user = User.objects.filter(id=user_id).first()

        if not user:
            cache.delete(_login_otp_cache_key(phone_norm))
            return JsonResponse({"success": False, "error": "Account not found."}, status=404)

        # Extra phone safety check
        local_phone = phone_norm[2:]  # 8801... -> 01...
        if str(user.phone_number) not in [phone_norm, local_phone]:
            return JsonResponse({"success": False, "error": "Phone number mismatch."}, status=400)

        login(request, user)

        # Remember me support
        if remember_me:
            request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
        else:
            request.session.set_expiry(0)  # browser close

        # Consume OTP after successful login
        cache.delete(_login_otp_cache_key(phone_norm))

        # Redirect target
        if user.user_type in [0, 2, 3, 4]:
            redirect_url = reverse("admin_dashboard")
        else:
            redirect_url = reverse("home")

        return JsonResponse({
            "success": True,
            "message": "OTP verified. Login successful.",
            "redirect_url": redirect_url
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def signin(request):
    if request.user.is_authenticated:
        if request.user.user_type == 3:
            return redirect('tcktbook')
        elif request.user.user_type in [0, 2, 4]:
            return redirect('admin_dashboard')
        return redirect('home')

    if request.method == 'POST':
        next_url = request.POST.get('next') or request.GET.get('next')
        login_mode = (request.POST.get("login_mode") or "password").strip()

        # ---------- PASSWORD LOGIN ----------
        if login_mode == "password":
            form = CustomSignInForm(request.POST)

            if form.is_valid():
                phone_number = form.cleaned_data['phone_number']
                password = form.cleaned_data['password']

                user = authenticate(request, phone_number=phone_number, password=password)

                if user is not None:
                    login(request, user)

                    if request.POST.get("remember_me"):
                        request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
                    else:
                        request.session.set_expiry(0)

                    messages.success(request, "Login Successful!")

                    if next_url:
                        return redirect(next_url)

                    if user.user_type == 3:
                        return redirect('tcktbook')
                    elif user.user_type in [0, 2, 4]:
                        return redirect('admin_dashboard')
                    return redirect('home')
                else:
                    messages.error(request, "Invalid phone number or password.")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

        # ---------- OTP LOGIN ----------
        elif login_mode == "otp":
            phone_raw = (request.POST.get("phone_number") or "").strip()
            otp_code = (request.POST.get("otp_code") or "").strip()

            if not phone_raw:
                messages.error(request, "Phone number is required.")
                return render(request, 'accounts/auth/signin.html', {
                    'form': CustomSignInForm(),
                    'otp_mode_active': True
                })

            if not otp_code:
                messages.error(request, "OTP is required.")
                return render(request, 'accounts/auth/signin.html', {
                    'form': CustomSignInForm(),
                    'otp_mode_active': True
                })

            phone_norm = _normalize_bd_phone(phone_raw)
            payload = cache.get(_login_otp_cache_key(phone_norm))

            if not isinstance(payload, dict):
                messages.error(request, "OTP expired. Please request a new OTP.")
                return render(request, 'accounts/auth/signin.html', {
                    'form': CustomSignInForm(),
                    'otp_mode_active': True
                })

            if not payload.get("verified"):
                messages.error(request, "Please verify OTP first.")
                return render(request, 'accounts/auth/signin.html', {
                    'form': CustomSignInForm(),
                    'otp_mode_active': True
                })

            User = get_user_model()
            user_id = payload.get("user_id")
            user = User.objects.filter(id=user_id).first()

            if not user:
                messages.error(request, "Account not found.")
                return render(request, 'accounts/auth/signin.html', {
                    'form': CustomSignInForm(),
                    'otp_mode_active': True
                })

            # Extra safety: phone must still match
            local_phone = "0" + phone_norm[2:]
            if str(user.phone_number) not in [phone_norm, local_phone]:
                messages.error(request, "Phone number mismatch. Please try again.")
                return render(request, 'accounts/auth/signin.html', {
                    'form': CustomSignInForm(),
                    'otp_mode_active': True
                })

            login(request, user)

            if request.POST.get("remember_me"):
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)

            # Consume OTP after login
            cache.delete(_login_otp_cache_key(phone_norm))

            messages.success(request, "Login Successful!")

            if next_url:
                return redirect(next_url)

            if user.user_type == 3:
                return redirect('tcktbook')
            elif user.user_type in [0, 2, 4]:
                return redirect('admin_dashboard')
            return redirect('home')

        else:
            messages.error(request, "Invalid login mode.")

    else:
        form = CustomSignInForm()

    return render(request, 'accounts/auth/signin.html', {'form': form})



def signup(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = CustomSignUpForm(request.POST)
        if form.is_valid():
            # Get data
            phone_number = form.cleaned_data['phone_number'] 
            email = form.cleaned_data['email'] # CHANGED: No longer optional, direct fetch
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            
            try:
                user = User.objects.create_user(
                    phone_number=phone_number, 
                    email=email, 
                    password=password, 
                    first_name=first_name, 
                    last_name=last_name,
                    user_type=1 # Customer
                )
                user.save()
                
                login(request, user)
                messages.success(request, "Account created successfully!")
                return redirect('home')
                
            except Exception as e:
                messages.error(request, f"Error creating account: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
    else:
        form = CustomSignUpForm()

    return render(request, 'accounts/auth/signup.html', {'form': form})

def signout(request):
    logout(request)
    messages.info(request, "You have logged out.")
    return redirect('signin')