from admin_panel.models import *

def global_site_identity(request):
    # This fetches the logo database object
    identity = SiteIdentity.objects.last()
    
    # This makes 'site_identity' available in ALL HTML templates
    return {'site_identity': identity}