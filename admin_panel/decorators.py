from django.contrib.auth.decorators import user_passes_test

def admin_only(view_func):
    """
    Decorator that checks if the user is a Superuser OR has user_type=0 (Admin).
    If not, it redirects them to the login page (or wherever you specify).
    """
    def check_user(user):
        # Adjust '0' if your Admin type is different
        return user.is_authenticated and (user.is_superuser or getattr(user, 'user_type', None) == 0)
    
    return user_passes_test(check_user, login_url='home')(view_func)