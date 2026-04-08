from admin_panel.models import *

def global_site_identity(request):
    # This fetches the logo database object
    identity = SiteIdentity.objects.last()
    
    # This makes 'site_identity' available in ALL HTML templates
    return {'site_identity': identity}


def footer_data(request):
    # Changed 'footercontent_set' to 'contents'
    footer_columns = FooterColumn.objects.prefetch_related('contents').order_by('order')
    social_settings = FooterSocialSettings.objects.order_by('id').first()
    footer_social_links = []

    if social_settings:
        if social_settings.facebook_url:
            footer_social_links.append({'platform': 'facebook', 'url': social_settings.facebook_url})
        if social_settings.instagram_url:
            footer_social_links.append({'platform': 'instagram', 'url': social_settings.instagram_url})
        if social_settings.youtube_url:
            footer_social_links.append({'platform': 'youtube', 'url': social_settings.youtube_url})
        if social_settings.linkedin_url:
            footer_social_links.append({'platform': 'linkedin', 'url': social_settings.linkedin_url})

    return {
        'footer_columns': footer_columns,
        'footer_social_links': footer_social_links,
    }
