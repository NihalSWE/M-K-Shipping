from django import forms
from .models import *
from django.core.validators import MaxLengthValidator
from django.contrib.auth import get_user_model

User = get_user_model()


class HomeBannerForm(forms.ModelForm):
    class Meta:
        model = HomeBanner
        fields = ['title', 'description', 'logo', 'background_image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter banner title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter description','maxlength': '107',}),
            # 'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'background_image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'background_image': 'Recommended size: 1760x500 pixels for best display.',
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].validators.append(MaxLengthValidator(107))
   
   
class BlogBannerForm(forms.ModelForm):
    class Meta:
        model = BlogBanner
        fields = ['title', 'background_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'background_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }   
        
        
class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'image', 'content', 'read_time']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter blog title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your content here...'}),
            'read_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5 Min Read'}),
            # Image input usually doesn't need a class if using default file input, but we can add one
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            
        }
        
        
        
class AdminUserAddForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Enter Password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Confirm Password'
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'user_type', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"]) # Hashes the password
        if commit:
            user.save()
        return user
    
    
    
class TripSearchForm(forms.Form):
    from_location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': 'Select Destination'}),
        label="From"
    )
    to_location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': 'Select Destination'}),
        label="To"
    )
    journey_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Journey Date"
    )

    def clean(self):
        cleaned_data = super().clean()
        loc_from = cleaned_data.get("from_location")
        loc_to = cleaned_data.get("to_location")

        if loc_from and loc_to and loc_from == loc_to:
            raise forms.ValidationError("Source and Destination cannot be the same.")
        
        

class CompanyOverviewForm(forms.ModelForm):
    class Meta:
        model = CompanyOverview
        fields = ['title', 'description', 'key_points', 'image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Title'}),
            
            # ID for Description Editor
            'description': forms.Textarea(attrs={'class': 'form-control', 'id': 'editor-desc', 'rows': 5}),
            
            # ID for Key Points Editor
            'key_points': forms.Textarea(attrs={'class': 'form-control', 'id': 'editor-points', 'rows': 5}),
            
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        
        
class AboutStoryForm(forms.ModelForm):
    class Meta:
        model = AboutStory
        fields = ['title', 'description', 'story_image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Main Title'}),
            'story_image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ['name', 'designation', 'description', 'image'] # Added description here
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Name'}),
            'designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Job Title'}),
            
            # Widget for the new description field
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter their quote or point of view...'}),
            
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }