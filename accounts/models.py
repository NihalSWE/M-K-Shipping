from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.conf import settings






class UserManager(BaseUserManager):
    # CHANGED: 'phone_number' is now the first required argument. 'email' is optional (None).
    def create_user(self, phone_number, email=None, username=None, password=None, user_type=1, **extra_fields):
        
        # CHANGED: Check for phone_number instead of email
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
            
        # CHANGED: Only normalize email if it is provided
        if email:
            email = self.normalize_email(email)
            
        extra_fields['user_type'] = user_type
        
        # CHANGED: Username generation logic
        # If no username provided, we use the phone_number as the default username
        username = extra_fields.get('username')
        if not username:
            username = phone_number
            # Ensure uniqueness just in case (though phone is usually unique)
            original_username = username
            counter = 1
            while self.model.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            extra_fields['username'] = username

        # CHANGED: Passed phone_number to the model
        user = self.model(phone_number=phone_number, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    # CHANGED: create_superuser now expects phone_number
    def create_superuser(self, phone_number, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 0)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # If username is not provided for superuser, default to phone_number
        if not username:
            username = phone_number

        return self.create_user(
            phone_number=phone_number,
            email=email,
            username=username,
            password=password,
            **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        (0, 'Admin'),
        (1, 'Customer'),
        (2, 'Staff'),
    )

    STATUS_CHOICES = (
        (0, 'Inactive'),
        (1, 'Active'),
        (2, 'Suspended'),
    )

    user_id = models.CharField(unique=True, max_length=15, blank=True, null=True)
    username = models.CharField(unique=True, max_length=150, blank=True, null=True)
    
    # CHANGED: Email is now optional (blank=True, null=True). 
    # specific 'unique=True' is kept so if they DO provide an email, it must be unique.
    email = models.EmailField(unique=True, max_length=100, blank=True, null=True)
    
    # CHANGED: Phone number is now strictly required (removed blank=True, null=True) and UNIQUE
    phone_number = models.CharField(max_length=20, unique=True)
    
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)
    city = models.CharField(max_length=250, blank=True, null=True)
    state = models.CharField(max_length=250, blank=True, null=True)
    postal_code = models.CharField(max_length=50, blank=True, null=True)
    company_name = models.CharField(max_length=150, blank=True, null=True)
    
    is_guest = models.BooleanField(
        default=False,
        help_text="True if the account was auto-created during booking and not yet claimed by the user."
    )

    user_type = models.IntegerField(choices=USER_TYPE_CHOICES, default=2)
    user_status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    
    assigned_counter = models.ForeignKey(
        'admin_panel.Counter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Counter this staff/admin user belongs to (if any)."
    )
    
    balance = models.FloatField(default=0.0)
    credit_limit = models.FloatField(default=0.0)
    
    proxy_ip = models.GenericIPAddressField(
        protocol='IPv4', 
        blank=True, 
        null=True, 
        help_text="The IP of the Customer's VPS (Squid Proxy)."
    )
    proxy_port = models.PositiveIntegerField(
        default=3128, 
        blank=True, 
        null=True, 
        help_text="Default Squid port is 3128."
    )
    proxy_username = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Optional: If you secure the Squid proxy with a password."
    )
    proxy_password = models.CharField(
        max_length=100, 
        blank=True, 
        null=True
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='razer_users_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_query_name='razer_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='razer_users_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_query_name='razer_user',
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    # CHANGED: This tells Django to use phone_number for login
    USERNAME_FIELD = 'phone_number'
    
    # CHANGED: Fields asked when running 'createsuperuser' (besides phone_number and password)
    # We add email here so you can still set it for admins if you want, but it's not strictly required by the db
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        # CHANGED: Prefer phone number for display
        return self.phone_number or self.username or self.email or f"User {self.pk}"
    
    def get_display_name(self):
        return self.first_name or self.last_name or self.username or self.phone_number
    
    
    
class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    hire_date = models.DateField(null=True, blank=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    linkedin_profile = models.URLField(blank=True, null=True)
    github_profile = models.URLField(blank=True, null=True)
    biography = models.TextField(blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.user.email