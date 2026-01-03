from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CustomSignUpForm, CustomSignInForm
from .models import User

def signin(request):
    if request.user.is_authenticated:
        return redirect('home') # Redirect if already logged in

    if request.method == 'POST':
        form = CustomSignInForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            # Authenticate using Email
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, "Login Successful!")
                # Redirect based on user type if needed, or just to home
                return redirect('home')
            else:
                messages.error(request, "Invalid email or password.")
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
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            
            # Create User (Force user_type=1 for Customer)
            try:
                user = User.objects.create_user(
                    email=email, 
                    password=password, 
                    first_name=first_name, 
                    last_name=last_name,
                    user_type=1 # Customer
                )
                user.save()
                
                # Log them in immediately
                login(request, user)
                messages.success(request, "Account created successfully!")
                return redirect('home')
                
            except Exception as e:
                messages.error(request, f"Error creating account: {e}")
        else:
            # Show form errors
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