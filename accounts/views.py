from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CustomSignUpForm, CustomSignInForm
from .models import User

def signin(request):
    if request.user.is_authenticated:
        if request.user.user_type in [0, 2]: 
            return redirect('admin_dashboard')
        return redirect('home')

    if request.method == 'POST':
        form = CustomSignInForm(request.POST)
        if form.is_valid():
            # CHANGED: Get phone_number instead of email
            phone_number = form.cleaned_data['phone_number']
            password = form.cleaned_data['password']
            
            # CHANGED: Authenticate using phone_number
            # Note: Because we set USERNAME_FIELD = 'phone_number' in models, 
            # we pass it as a keyword argument here.
            user = authenticate(request, phone_number=phone_number, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, "Login Successful!")
                
                if user.user_type == 0 or user.user_type == 2:
                    return redirect('admin_dashboard')
                else:
                    return redirect('home')
            else:
                # CHANGED: Error message
                messages.error(request, "Invalid phone number or password.")
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
            phone_number = form.cleaned_data['phone_number'] # CHANGED
            email = form.cleaned_data.get('email') # CHANGED: .get() because it's optional
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            
            try:
                # CHANGED: create_user now requires phone_number as first arg
                user = User.objects.create_user(
                    phone_number=phone_number, 
                    email=email, 
                    password=password, 
                    first_name=first_name, 
                    last_name=last_name,
                    user_type=1 # Customer
                )
                # User is saved inside create_user, but calling save() again is harmless
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