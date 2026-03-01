from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Agent

class AgentSitemap(Sitemap):
    # Tells Google these pages update weekly (e.g. new articles, reviews)
    changefreq = "weekly"
    
    # Priority from 0.0 to 1.0 (0.8 means these are highly important pages)
    priority = 0.8

    def items(self):
        # We only want to index agents who are public and live
        return Agent.objects.filter(is_public=True)

    def location(self, obj):
        # This dynamically builds their exact URL path (e.g., /agent/lakshan/)
        return reverse('agent_profile', kwargs={'slug': obj.slug})