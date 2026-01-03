from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.conf import settings






class UserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None, user_id=None, user_type=1, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        extra_fields['user_type'] = user_type
        
        # Check if a username is provided, otherwise generate one from the email
        username = extra_fields.get('username')
        if not username:
            # Generates a unique username from the email
            # Example: 'john.doe@example.com' -> 'john.doe'
            username = email.split('@')[0]
            # Ensure uniqueness, append a number if necessary
            original_username = username
            counter = 1
            while self.model.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            extra_fields['username'] = username

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, user_id=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 0)

        # Let create_user handle user_id generation
        return self.create_user(
            email=email,
            username=username,
            password=password,
            user_id=user_id,  # Can be None
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
    email = models.EmailField(unique=True, max_length=100)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)
    city = models.CharField(max_length=250, blank=True, null=True)
    state = models.CharField(max_length=250, blank=True, null=True)
    postal_code = models.CharField(max_length=50, blank=True, null=True)
    company_name = models.CharField(max_length=150, blank=True, null=True) 
    # package = models.ForeignKey('Package', on_delete=models.SET_NULL, null=True, blank=True)

    user_type = models.IntegerField(choices=USER_TYPE_CHOICES, default=2)
    user_status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    
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
    
    # Add unique related_name arguments to avoid clashes
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='razer_users_groups', # A unique name
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_query_name='razer_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='razer_users_permissions', # A unique name
        blank=True,
        help_text='Specific permissions for this user.',
        related_query_name='razer_user',
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username or self.email or f"User {self.pk}"
    
    def get_display_name(self):
        """Return the best available name for displaying the user."""
        return self.first_name or self.last_name or self.username or self.email
    
    
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