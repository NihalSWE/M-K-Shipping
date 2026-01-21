from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User

# 1. Sign Up Form
class CustomSignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        # CHANGED: Added phone_number to fields, kept email as optional
        fields = ['first_name', 'last_name', 'phone_number', 'email', 'password']

    # CHANGED: Logic to check if phone number already exists
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if User.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone_number

    # OPTIONAL: You can keep clean_email if you still want unique emails (when provided)
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Only check if email is actually provided (since it's now optional)
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data

# 2. Sign In Form (Switched EmailField to CharField for Phone)
class CustomSignInForm(forms.Form):
    phone_number = forms.CharField(
        label="Phone Number",
        widget=forms.TextInput(attrs={'placeholder': 'Enter your phone number'})
    )
    password = forms.CharField(widget=forms.PasswordInput)
    
    
    
class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'user_type', 'user_status', 'is_active',
            'balance', 'credit_limit',
            'company_name', 'city'
        ]